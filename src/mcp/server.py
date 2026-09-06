"""
MCP Server 实现
"""
import asyncio
import json
import logging
from typing import Any, List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.models.database import Message, Channel
from ..api.models.schemas import Platform, Sentiment, SearchQuery
from ..core.database import get_db

logger = logging.getLogger(__name__)


class MCPTool:
    """MCP 工具定义"""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: callable,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler


class MCPServer:
    """MCP Server 实现
    
    提供给 AI Agent 使用的搜索工具
    """
    
    def __init__(self):
        self.name = "social-feed-aggregator"
        self.version = "1.0.0"
        self._tools: dict[str, MCPTool] = {}
        self._register_tools()
    
    def _register_tools(self):
        """注册所有工具"""
        self._tools["search_messages"] = MCPTool(
            name="search_messages",
            description="搜索社交媒体消息，支持多条件过滤",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["all", "discord", "reddit", "qq", "wecom"],
                        "description": "渠道类型",
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签过滤",
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative"],
                        "description": "情感倾向",
                    },
                    "author": {
                        "type": "string",
                        "description": "作者名称",
                    },
                    "since": {
                        "type": "string",
                        "format": "date-time",
                        "description": "开始时间 (ISO 8601)",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                        "description": "返回数量限制",
                    },
                },
                "required": ["query"],
            },
            handler=self._search_messages,
        )
        
        self._tools["get_message_detail"] = MCPTool(
            name="get_message_detail",
            description="获取消息详情",
            input_schema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "消息 UUID",
                    },
                },
                "required": ["message_id"],
            },
            handler=self._get_message_detail,
        )
        
        self._tools["get_channel_summary"] = MCPTool(
            name="get_channel_summary",
            description="获取渠道统计摘要",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "渠道 UUID",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["today", "week", "month", "all"],
                        "default": "week",
                        "description": "统计周期",
                    },
                },
            },
            handler=self._get_channel_summary,
        )
        
        self._tools["list_channels"] = MCPTool(
            name="list_channels",
            description="列出所有渠道",
            input_schema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["all", "discord", "reddit", "qq", "wecom"],
                        "description": "平台类型",
                    },
                    "enabled_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "只显示启用的渠道",
                    },
                },
            },
            handler=self._list_channels,
        )
    
    def get_tools(self) -> List[dict]:
        """获取所有工具定义"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]
    
    async def call_tool(
        self,
        name: str,
        arguments: dict,
        db: AsyncSession,
    ) -> dict:
        """调用工具"""
        if name not in self._tools:
            raise HTTPException(status_code=404, detail=f"Tool not found: {name}")
        
        tool = self._tools[name]
        
        try:
            result = await tool.handler(db, arguments)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _search_messages(
        self,
        db: AsyncSession,
        args: dict,
    ) -> List[dict]:
        """搜索消息"""
        query = args.get("query", "")
        channel_filter = args.get("channel", "all")
        categories = args.get("categories")
        sentiment = args.get("sentiment")
        author = args.get("author")
        since = args.get("since")
        limit = min(args.get("limit", 20), 100)
        
        # 构建查询
        stmt = select(Message, Channel).join(
            Channel, Message.channel_id == Channel.id
        ).where(Message.is_deleted == False)
        
        # 全文搜索
        if query:
            stmt = stmt.where(
                Message.content.ilike(f"%{query}%")
            )
        
        # 渠道过滤
        if channel_filter and channel_filter != "all":
            stmt = stmt.where(Channel.platform == channel_filter)
        
        # 标签过滤
        if categories:
            stmt = stmt.where(Message.categories.overlap(categories))
        
        # 情感过滤
        if sentiment:
            stmt = stmt.where(Message.sentiment == sentiment)
        
        # 作者过滤
        if author:
            stmt = stmt.where(Message.author_name.ilike(f"%{author}%"))
        
        # 时间过滤
        if since:
            stmt = stmt.where(Message.created_at >= since)
        
        # 排序和限制
        stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        return [
            {
                "id": str(msg.id),
                "platform": channel.platform.value,
                "channel_name": msg.channel_name,
                "author_name": msg.author_name,
                "content": msg.content,
                "sentiment": msg.sentiment.value if msg.sentiment else None,
                "categories": msg.categories or [],
                "created_at": msg.created_at.isoformat(),
                "url": _generate_message_url(channel.platform.value, msg),
            }
            for msg, channel in rows
        ]
    
    async def _get_message_detail(
        self,
        db: AsyncSession,
        args: dict,
    ) -> dict:
        """获取消息详情"""
        message_id = args.get("message_id")
        
        stmt = select(Message, Channel).join(
            Channel, Message.channel_id == Channel.id
        ).where(Message.id == UUID(message_id))
        
        result = await db.execute(stmt)
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Message not found")
        
        msg, channel = row
        
        return {
            "id": str(msg.id),
            "platform": channel.platform.value,
            "channel_name": msg.channel_name,
            "author_id": msg.author_id,
            "author_name": msg.author_name,
            "content": msg.content,
            "sentiment": msg.sentiment.value if msg.sentiment else None,
            "categories": msg.categories or [],
            "entities": msg.entities or {},
            "summary": msg.summary,
            "attachments": msg.attachments or [],
            "metadata": msg.metadata or {},
            "created_at": msg.created_at.isoformat(),
            "analyzed": msg.analyzed,
        }
    
    async def _get_channel_summary(
        self,
        db: AsyncSession,
        args: dict,
    ) -> dict:
        """获取渠道摘要"""
        channel_id = args.get("channel_id")
        period = args.get("period", "week")
        
        from datetime import datetime, timedelta
        
        # 计算时间范围
        now = datetime.utcnow()
        if period == "today":
            since = now.replace(hour=0, minute=0, second=0)
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "month":
            since = now - timedelta(days=30)
        else:
            since = None
        
        # 构建查询
        if channel_id:
            stmt = select(Message).where(
                and_(
                    Message.channel_id == UUID(channel_id),
                    Message.is_deleted == False,
                )
            )
            if since:
                stmt = stmt.where(Message.created_at >= since)
        else:
            stmt = select(Message).where(Message.is_deleted == False)
            if since:
                stmt = stmt.where(Message.created_at >= since)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        # 统计
        total = len(messages)
        sentiments = {"positive": 0, "neutral": 0, "negative": 0}
        category_counts = {}
        
        for msg in messages:
            if msg.sentiment:
                sentiments[msg.sentiment.value] += 1
            
            if msg.categories:
                for cat in msg.categories:
                    category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Top categories
        top_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "period": period,
            "total_messages": total,
            "sentiment_distribution": sentiments,
            "top_categories": [
                {"category": cat, "count": count}
                for cat, count in top_categories
            ],
        }
    
    async def _list_channels(
        self,
        db: AsyncSession,
        args: dict,
    ) -> List[dict]:
        """列出渠道"""
        platform_filter = args.get("platform", "all")
        enabled_only = args.get("enabled_only", True)
        
        stmt = select(Channel)
        
        if platform_filter and platform_filter != "all":
            stmt = stmt.where(Channel.platform == platform_filter)
        
        if enabled_only:
            stmt = stmt.where(Channel.enabled == True)
        
        stmt = stmt.order_by(Channel.name)
        
        result = await db.execute(stmt)
        channels = result.scalars().all()
        
        return [
            {
                "id": str(ch.id),
                "platform": ch.platform.value,
                "name": ch.name,
                "description": ch.description,
                "enabled": ch.enabled,
            }
            for ch in channels
        ]


# ============ MCP HTTP API ============

from fastapi import APIRouter

mcp_router = APIRouter(prefix="/mcp", tags=["MCP"])
mcp_server = MCPServer()


@mcp_router.get("/tools")
async def list_tools():
    """列出所有可用工具"""
    return {"tools": mcp_server.get_tools()}


@mcp_router.post("/call")
async def call_tool(
    name: str,
    arguments: dict,
    db: AsyncSession = Depends(get_db),
):
    """调用 MCP 工具"""
    return await mcp_server.call_tool(name, arguments, db)


def _generate_message_url(platform: str, message: Message) -> Optional[str]:
    """生成消息链接"""
    # 各平台的链接格式
    if platform == "discord":
        if message.metadata:
            guild_id = message.metadata.get("guild_id")
            channel_id = message.metadata.get("channel_id")
            if guild_id and channel_id:
                return f"https://discord.com/channels/{guild_id}/{channel_id}/{message.platform_message_id}"
    
    elif platform == "reddit":
        if message.metadata:
            permalink = message.metadata.get("permalink")
            if permalink:
                return f"https://reddit.com{permalink}"
    
    return None
