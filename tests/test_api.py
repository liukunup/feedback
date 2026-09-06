"""
API 路由测试
"""
import pytest
from datetime import datetime
from uuid import uuid4


class TestHealthEndpoint:
    """测试健康检查端点"""
    
    def test_health_check(self):
        """测试健康检查"""
        from src.api.main import app
        
        # 测试 app 可以导入
        assert app is not None
        assert app.title == "Social Feed Aggregator"


class TestAPIRoutes:
    """测试 API 路由"""
    
    def test_channels_router_exists(self):
        """测试 channels 路由存在"""
        from src.api.routers.channels import router
        
        assert router is not None
        assert len(router.routes) == 8
        
        # 检查路由路径
        paths = [r.path for r in router.routes]
        assert "/channels/" in paths
        assert "/channels/{channel_id}" in paths
        assert "/channels/{channel_id}/enable" in paths
        assert "/channels/{channel_id}/fetch" in paths
    
    def test_messages_router_exists(self):
        """测试 messages 路由存在"""
        from src.api.routers.messages import router
        
        assert router is not None
        paths = [r.path for r in router.routes]
        assert "/messages/" in paths
        assert "/messages/{message_id}" in paths
    
    def test_search_router_exists(self):
        """测试 search 路由存在"""
        from src.api.routers.search import router
        
        assert router is not None
        paths = [r.path for r in router.routes]
        assert "/search/" in paths
        assert "/search/stats" in paths
        assert "/search/categories" in paths
    
    def test_mcp_router_exists(self):
        """测试 MCP 路由存在"""
        from src.mcp.server import mcp_router
        
        assert mcp_router is not None


class TestSchemas:
    """测试 Schema 验证"""
    
    def test_channel_create_validation(self):
        """测试渠道创建 schema 验证"""
        from src.api.models.schemas import ChannelCreate, Platform as SchemaPlatform
        
        # 正常数据
        data = ChannelCreate(
            platform=SchemaPlatform.DISCORD,
            name="Test Channel",
            config={"token": "abc123"},
        )
        assert data.platform == SchemaPlatform.DISCORD
        assert data.name == "Test Channel"
    
    def test_search_query_validation(self):
        """测试搜索查询 schema"""
        from src.api.models.schemas import SearchQuery, Platform as SchemaPlatform, Sentiment as SchemaSentiment
        
        data = SearchQuery(
            query="测试搜索",
            platforms=[SchemaPlatform.DISCORD, SchemaPlatform.REDDIT],
            sentiment=SchemaSentiment.POSITIVE,
            page=1,
            page_size=20,
        )
        assert data.query == "测试搜索"
        assert len(data.platforms) == 2
        assert data.sentiment == SchemaSentiment.POSITIVE
    
    def test_message_response_validation(self):
        """测试消息响应 schema"""
        from src.api.models.schemas import MessageResponse
        from uuid import uuid4
        
        msg_id = uuid4()
        channel_id = uuid4()
        
        data = MessageResponse(
            id=msg_id,
            channel_id=channel_id,
            platform_message_id="msg-123",
            content="Test content",
            author_id="user1",
            author_name="Test User",
            created_at=datetime.now(),
            analyzed=True,
        )
        assert data.content == "Test content"
        assert data.analyzed == True


class TestScraperRegistry:
    """测试 Scraper 注册表"""
    
    def test_platform_registration(self):
        """测试平台注册"""
        from src.scrapers.base import ScraperRegistry, Platform
        
        platforms = ScraperRegistry.list_platforms()
        assert Platform.DISCORD in platforms
        assert Platform.REDDIT in platforms
        assert Platform.QQ in platforms
        assert Platform.WECOM in platforms
    
    def test_get_scraper_by_platform(self):
        """测试根据平台获取 scraper"""
        from src.scrapers.base import ScraperRegistry, Platform
        
        for platform in Platform:
            scraper = ScraperRegistry.get_scraper(platform)
            assert scraper is not None
            assert scraper.platform == platform
    
    def test_invalid_platform(self):
        """测试无效平台"""
        from src.scrapers.base import ScraperRegistry
        
        with pytest.raises(ValueError):
            ScraperRegistry.get_scraper("invalid_platform")


class TestMessageConversion:
    """测试消息格式转换"""
    
    def test_message_to_dict(self):
        """测试 Message 转为字典"""
        from src.scrapers.base import Message
        
        msg = Message(
            platform_id="123",
            content="Hello World",
            author_id="user1",
            author_name="User One",
            created_at=datetime.now(),
            metadata={"key": "value"},
            attachments=[{"type": "image", "url": "http://example.com/img.jpg"}],
        )
        
        data = msg.to_dict()
        
        assert data["platform_message_id"] == "123"
        assert data["content"] == "Hello World"
        assert data["author_id"] == "user1"
        assert data["author_name"] == "User One"
        assert data["metadata"] == {"key": "value"}
        assert len(data["attachments"]) == 1


class TestConfigSettings:
    """测试配置"""
    
    def test_settings_defaults(self):
        """测试默认配置"""
        from src.core.config import Settings
        
        settings = Settings()
        
        # 检查默认值
        assert settings.fetch_interval_seconds == 300
        assert settings.fetch_batch_size == 100
        assert settings.max_retries == 3
        assert settings.ai_model == "gpt-4o-mini"
    
    def test_platform_enum(self):
        """测试平台枚举"""
        from src.api.models.schemas import Platform
        
        assert Platform.DISCORD.value == "discord"
        assert Platform.REDDIT.value == "reddit"
        assert Platform.QQ.value == "qq"
        assert Platform.WECOM.value == "wecom"


class TestSentimentEnum:
    """测试情感枚举"""
    
    def test_sentiment_values(self):
        """测试情感枚举值"""
        from src.api.models.schemas import Sentiment
        
        assert Sentiment.POSITIVE.value == "positive"
        assert Sentiment.NEUTRAL.value == "neutral"
        assert Sentiment.NEGATIVE.value == "negative"


class TestFetchStatusEnum:
    """测试抓取状态枚举"""
    
    def test_fetch_status_values(self):
        """测试抓取状态枚举值"""
        from src.api.models.database import FetchStatus
        
        assert FetchStatus.SUCCESS.value == "success"
        assert FetchStatus.FAILED.value == "failed"
        assert FetchStatus.PARTIAL.value == "partial"


class TestMCPServer:
    """测试 MCP Server"""
    
    def test_mcp_tools_available(self):
        """测试 MCP 工具可用"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tools = server.get_tools()
        
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "search_messages" in tool_names
        assert "get_message_detail" in tool_names
        assert "get_channel_summary" in tool_names
        assert "list_channels" in tool_names
    
    def test_search_messages_tool_schema(self):
        """测试搜索工具 schema"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tools = server.get_tools()
        
        search_tool = next(t for t in tools if t["name"] == "search_messages")
        schema = search_tool["inputSchema"]
        
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["properties"]
        assert schema["properties"]["query"]["type"] == "string"
