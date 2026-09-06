"""
测试模块
"""
import pytest
from datetime import datetime
from uuid import uuid4


class TestScraperBase:
    """测试 Scraper 基类"""
    
    def test_message_dataclass(self):
        """测试 Message 数据类"""
        from src.scrapers.base import Message
        
        msg = Message(
            platform_id="123",
            content="Test message",
            author_id="user1",
            author_name="Test User",
            created_at=datetime.now(),
        )
        
        assert msg.platform_id == "123"
        assert msg.content == "Test message"
        assert msg.author_id == "user1"
        assert msg.author_name == "Test User"
    
    def test_message_to_dict(self):
        """测试 Message 转换为字典"""
        from src.scrapers.base import Message
        
        msg = Message(
            platform_id="123",
            content="Test",
            author_id="u1",
            author_name="User",
            created_at=datetime.now(),
        )
        
        data = msg.to_dict()
        assert data["platform_message_id"] == "123"
        assert data["content"] == "Test"


class TestChannelConfig:
    """测试 ChannelConfig"""
    
    def test_channel_config_creation(self):
        """测试创建 ChannelConfig"""
        from src.scrapers.base import ChannelConfig, Platform
        
        config = ChannelConfig(
            channel_id="ch-1",
            platform=Platform.DISCORD,
            access_token="token123",
            extra_config={"key": "value"},
        )
        
        assert config.channel_id == "ch-1"
        assert config.platform == Platform.DISCORD
        assert config.access_token == "token123"


class TestAIAnalyzer:
    """测试 AI 分析器"""
    
    @pytest.mark.asyncio
    async def test_analyzer_returns_result(self):
        """测试分析器返回结果"""
        from src.workers.processors.analyzers.openai_analyzer import (
            MessageAnalyzer, Sentiment, AnalysisResult
        )
        
        analyzer = MessageAnalyzer()
        result = await analyzer.analyze("这个产品很好用！")
        
        assert isinstance(result, AnalysisResult)
        assert result.sentiment in [Sentiment.POSITIVE, Sentiment.NEUTRAL, Sentiment.NEGATIVE]


class TestDatabaseModels:
    """测试数据库模型"""
    
    def test_channel_model(self):
        """测试 Channel 模型"""
        from src.api.models.database import Channel
        
        channel = Channel(
            platform="discord",  # 使用字符串值
            name="Test Channel",
            config={"token": "test"},
            enabled=True,
        )
        
        assert channel.platform == "discord"
        assert channel.name == "Test Channel"
        assert channel.enabled == True
    
    def test_message_model(self):
        """测试 Message 模型"""
        from src.api.models.database import Message
        
        msg = Message(
            channel_id=uuid4(),
            platform_message_id="msg-123",
            content="Hello",
            author_id="user1",
            author_name="User",
            created_at=datetime.now(),
        )
        
        assert msg.platform_message_id == "msg-123"
        assert msg.content == "Hello"


class TestAPISchemas:
    """测试 API Schemas"""
    
    def test_channel_create_schema(self):
        """测试创建渠道 Schema"""
        from src.api.models.schemas import ChannelCreate, Platform as SchemaPlatform
        
        data = ChannelCreate(
            platform=SchemaPlatform.DISCORD,
            name="My Channel",
            config={"token": "abc"},
        )
        
        assert data.platform == SchemaPlatform.DISCORD
        assert data.name == "My Channel"
    
    def test_message_response_schema(self):
        """测试消息响应 Schema"""
        from src.api.models.schemas import MessageResponse
        from uuid import uuid4
        
        data = MessageResponse(
            id=uuid4(),
            channel_id=uuid4(),
            platform_message_id="msg-1",
            content="Test",
            author_id="u1",
            author_name="User",
            created_at=datetime.now(),
            analyzed=False,
        )
        
        assert data.content == "Test"


class TestMCP:
    """测试 MCP Server"""
    
    @pytest.mark.asyncio
    async def test_mcp_tools_list(self):
        """测试获取工具列表"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tools = server.get_tools()
        
        assert len(tools) > 0
        assert any(t["name"] == "search_messages" for t in tools)
