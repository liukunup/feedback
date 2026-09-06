"""
MCP Server 测试
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestMCPServerInit:
    """测试 MCP Server 初始化"""
    
    def test_server_initialization(self):
        """测试服务器初始化"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        
        assert server.name == "social-feed-aggregator"
        assert server.version == "1.0.0"
        assert len(server._tools) == 4
    
    def test_server_tools_registered(self):
        """测试工具已注册"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        
        expected_tools = [
            "search_messages",
            "get_message_detail",
            "get_channel_summary",
            "list_channels",
        ]
        
        for tool_name in expected_tools:
            assert tool_name in server._tools


class TestMCPToolDefinition:
    """测试 MCP 工具定义"""
    
    def test_search_messages_tool(self):
        """测试搜索工具定义"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tool = server._tools["search_messages"]
        
        assert tool.name == "search_messages"
        assert "query" in tool.input_schema["properties"]
        assert tool.input_schema["properties"]["query"]["type"] == "string"
        assert "limit" in tool.input_schema["properties"]
    
    def test_get_message_detail_tool(self):
        """测试获取消息详情工具"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tool = server._tools["get_message_detail"]
        
        assert tool.name == "get_message_detail"
        assert "message_id" in tool.input_schema["properties"]
        assert tool.input_schema["required"] == ["message_id"]
    
    def test_get_channel_summary_tool(self):
        """测试获取渠道摘要工具"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tool = server._tools["get_channel_summary"]
        
        assert tool.name == "get_channel_summary"
        assert "channel_id" in tool.input_schema["properties"]
        assert "period" in tool.input_schema["properties"]
        assert tool.input_schema["properties"]["period"]["enum"] == ["today", "week", "month", "all"]
    
    def test_list_channels_tool(self):
        """测试列出渠道工具"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tool = server._tools["list_channels"]
        
        assert tool.name == "list_channels"
        assert "platform" in tool.input_schema["properties"]
        assert "enabled_only" in tool.input_schema["properties"]


class TestMCPToolExecution:
    """测试 MCP 工具执行"""
    
    @pytest.mark.asyncio
    async def test_call_nonexistent_tool(self):
        """测试调用不存在的工具"""
        from src.mcp.server import MCPServer
        from fastapi import HTTPException
        
        server = MCPServer()
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await server.call_tool("nonexistent_tool", {}, mock_db)
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_search_messages_empty_results(self):
        """测试搜索消息空结果"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        mock_db = AsyncMock()
        
        # Mock the execute method to return empty results
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await server._search_messages(
            mock_db,
            {"query": "nonexistent", "limit": 10}
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_list_channels_empty(self):
        """测试列出渠道空结果"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        mock_db = AsyncMock()
        
        # Mock the execute method
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await server._list_channels(mock_db, {})
        
        assert result == []


class TestMCPToolSchemas:
    """测试工具 Schema 验证"""
    
    def test_search_messages_schema_complete(self):
        """测试搜索消息 Schema 完整性"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tools = server.get_tools()
        
        search_tool = next(t for t in tools if t["name"] == "search_messages")
        schema = search_tool["inputSchema"]
        
        # 检查必要字段
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["required"]
        
        # 检查各属性类型
        props = schema["properties"]
        assert props["query"]["type"] == "string"
        assert props["limit"]["type"] == "integer"
        assert props["limit"]["minimum"] == 1
        assert props["limit"]["maximum"] == 100
    
    def test_all_tools_have_required_fields(self):
        """测试所有工具都有必需字段"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tools = server.get_tools()
        
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]


class TestMessageURLGeneration:
    """测试消息 URL 生成"""
    
    def test_generate_discord_url(self):
        """测试生成 Discord 链接"""
        from src.mcp.server import _generate_message_url, Message
        from src.api.models.database import Platform
        
        msg = MagicMock()
        msg.platform_message_id = "123456"
        msg.metadata = {"guild_id": "111", "channel_id": "222"}
        
        url = _generate_message_url("discord", msg)
        
        assert url == "https://discord.com/channels/111/222/123456"
    
    def test_generate_reddit_url(self):
        """测试生成 Reddit 链接"""
        from src.mcp.server import _generate_message_url, Message
        
        msg = MagicMock()
        msg.platform_message_id = "abc"
        msg.metadata = {"permalink": "/r/technology/comments/xyz/test"}
        
        url = _generate_message_url("reddit", msg)
        
        assert url == "https://reddit.com/r/technology/comments/xyz/test"
    
    def test_generate_url_no_metadata(self):
        """测试没有元数据时返回 None"""
        from src.mcp.server import _generate_message_url
        
        msg = MagicMock()
        msg.platform_message_id = "123"
        msg.metadata = None
        
        url = _generate_message_url("discord", msg)
        
        assert url is None
    
    def test_generate_url_unknown_platform(self):
        """测试未知平台返回 None"""
        from src.mcp.server import _generate_message_url
        
        msg = MagicMock()
        msg.platform_message_id = "123"
        msg.metadata = {}
        
        url = _generate_message_url("unknown_platform", msg)
        
        assert url is None
