"""
存储处理器
"""
import logging
from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...scrapers.base import Message
from ...api.models.database import Message as DBMessage

logger = logging.getLogger(__name__)


class StorageProcessor:
    """消息存储处理器"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_messages(self, channel_id: UUID, messages: List[Message]) -> int:
        """保存消息到数据库
        
        Args:
            channel_id: 渠道 ID
            messages: 消息列表
            
        Returns:
            新增消息数量
        """
        new_count = 0
        
        for msg in messages:
            # 检查是否已存在
            existing = await self.session.execute(
                select(DBMessage).where(
                    and_(
                        DBMessage.channel_id == channel_id,
                        DBMessage.platform_message_id == msg.platform_id,
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                # 已存在，跳过
                continue
            
            # 创建新消息
            db_message = DBMessage(
                channel_id=channel_id,
                platform_message_id=msg.platform_id,
                content=msg.content,
                author_id=msg.author_id,
                author_name=msg.author_name,
                author_avatar=msg.author_avatar,
                created_at=msg.created_at,
                metadata=msg.metadata,
                attachments=msg.attachments,
                channel_name=msg.channel_name,
                analyzed=False,
            )
            
            self.session.add(db_message)
            new_count += 1
        
        await self.session.flush()
        
        if new_count > 0:
            logger.info(f"Saved {new_count} new messages for channel {channel_id}")
        
        return new_count
    
    async def get_message_by_platform_id(
        self, 
        channel_id: UUID, 
        platform_message_id: str
    ) -> DBMessage | None:
        """根据平台消息 ID 获取消息"""
        result = await self.session.execute(
            select(DBMessage).where(
                and_(
                    DBMessage.channel_id == channel_id,
                    DBMessage.platform_message_id == platform_message_id,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_message_analysis(
        self,
        message_id: UUID,
        sentiment: str,
        categories: List[str],
        entities: dict,
        summary: str,
    ) -> bool:
        """更新消息分析结果"""
        result = await self.session.execute(
            select(DBMessage).where(DBMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        if not message:
            return False
        
        message.sentiment = sentiment
        message.categories = categories
        message.entities = entities
        message.summary = summary
        message.analyzed = True
        
        await self.session.flush()
        return True
    
    async def soft_delete_message(self, message_id: UUID) -> bool:
        """软删除消息"""
        result = await self.session.execute(
            select(DBMessage).where(DBMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        if not message:
            return False
        
        message.is_deleted = True
        await self.session.flush()
        return True
    
    async def bulk_update_analyses(
        self,
        analyses: List[dict]
    ) -> int:
        """批量更新分析结果
        
        Args:
            analyses: [{"message_id": UUID, "sentiment": str, ...}]
            
        Returns:
            更新数量
        """
        updated = 0
        
        for analysis in analyses:
            success = await self.update_message_analysis(
                message_id=analysis["message_id"],
                sentiment=analysis.get("sentiment", "neutral"),
                categories=analysis.get("categories", []),
                entities=analysis.get("entities", {}),
                summary=analysis.get("summary", ""),
            )
            if success:
                updated += 1
        
        await self.session.flush()
        return updated
