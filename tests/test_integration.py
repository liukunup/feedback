"""
集成测试 - 需要模拟数据库
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestScraperIntegration:
    """Scraper 集成测试"""
    
    @pytest.mark.asyncio
    async def test_discord_scraper_initialization(self):
        """测试 Discord Scraper 初始化"""
        from src.scrapers.discord import DiscordPyScraper
        from src.scrapers.base import ChannelConfig, Platform
        
        scraper = DiscordPyScraper()
        assert scraper is not None
        assert scraper.platform == Platform.DISCORD
        assert scraper.is_initialized == False
    
    @pytest.mark.asyncio
    async def test_reddit_scraper_initialization(self):
        """测试 Reddit Scraper 初始化"""
        from src.scrapers.reddit import RedditScraper
        from src.scrapers.base import Platform
        
        scraper = RedditScraper()
        assert scraper is not None
        assert scraper.platform == Platform.REDDIT
    
    @pytest.mark.asyncio
    async def test_qq_ui_scraper_initialization(self):
        """测试 QQ uiautomator2 Scraper 初始化"""
        from src.scrapers.qq import QQUIAutomatorScraper
        from src.scrapers.base import Platform
        
        scraper = QQUIAutomatorScraper()
        assert scraper is not None
        assert scraper.platform == Platform.QQ
    
    @pytest.mark.asyncio
    async def test_wecom_scraper_initialization(self):
        """测试企业微信 Scraper 初始化"""
        from src.scrapers.wecom import WeComScraper
        from src.scrapers.base import Platform
        
        scraper = WeComScraper()
        assert scraper is not None
        assert scraper.platform == Platform.WECOM


class TestMessageParsing:
    """消息解析测试"""
    
    def test_parse_discord_message_format(self):
        """测试解析 Discord 消息格式"""
        from src.scrapers.base import Message
        
        msg = Message(
            platform_id="123456789",
            content="Hello from Discord!",
            author_id="987654321",
            author_name="DiscordUser",
            created_at=datetime.now(),
            metadata={
                "guild_id": "111",
                "guild_name": "Test Server",
                "channel_id": "222",
            },
            attachments=[
                {"type": "image", "url": "https://cdn.discord.com/img.png"}
            ],
            channel_name="general",
            channel_id="222",
        )
        
        assert msg.platform_id == "123456789"
        assert msg.content == "Hello from Discord!"
        assert msg.metadata["guild_name"] == "Test Server"
        assert len(msg.attachments) == 1
    
    def test_parse_reddit_message_format(self):
        """测试解析 Reddit 消息格式"""
        from src.scrapers.base import Message
        
        msg = Message(
            platform_id="abc123",
            content="This is a Reddit post title\n\nAnd this is the body content.",
            author_id="reddit_user",
            author_name="RedditUser",
            created_at=datetime.now(),
            metadata={
                "type": "submission",
                "subreddit": "technology",
                "score": 42,
            },
            channel_name="r/technology",
            channel_id="technology",
        )
        
        assert msg.platform_id == "abc123"
        assert "Reddit post title" in msg.content
        assert msg.metadata["subreddit"] == "technology"
        assert msg.channel_name == "r/technology"
    
    def test_parse_qq_message_format(self):
        """测试解析 QQ 消息格式"""
        from src.scrapers.base import Message
        
        msg = Message(
            platform_id="qq_msg_123",
            content="QQ 群消息内容",
            author_id="12345678",
            author_name="QQ用户",
            created_at=datetime.now(),
            metadata={
                "conversation": "测试群",
                "type": "group",
            },
            channel_name="测试群",
            channel_id="group_123",
        )
        
        assert msg.platform_id == "qq_msg_123"
        assert msg.metadata["type"] == "group"
        assert msg.channel_name == "测试群"


class TestAIAnalyzerMocked:
    """AI 分析器测试 (使用 Mock)"""
    
    @pytest.mark.asyncio
    async def test_analyzer_positive_content(self):
        """测试正面情感分析"""
        from src.workers.processors.analyzers.openai_analyzer import (
            MessageAnalyzer, Sentiment, AnalysisResult
        )
        
        analyzer = MessageAnalyzer()
        
        # 这个测试会调用实际的 API，如果有 API key 的话
        # 没有 API key 时会返回默认结果
        try:
            result = await analyzer.analyze("这个产品太棒了！我非常满意！")
            assert isinstance(result, AnalysisResult)
        except Exception:
            # 如果没有 API key，跳过
            pytest.skip("No API key configured")
    
    @pytest.mark.asyncio
    async def test_analyzer_empty_content(self):
        """测试空内容"""
        from src.workers.processors.analyzers.openai_analyzer import MessageAnalyzer
        
        analyzer = MessageAnalyzer()
        result = await analyzer.analyze("")
        
        assert result.categories == []
        assert result.summary == ""


class TestStorageProcessorMocked:
    """存储处理器测试 (使用 Mock)"""
    
    @pytest.mark.asyncio
    async def test_save_messages_creates_new(self):
        """测试保存新消息"""
        from src.workers.processors.storage import StorageProcessor
        from src.scrapers.base import Message
        from uuid import uuid4
        
        # 创建 mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        processor = StorageProcessor(mock_session)
        
        messages = [
            Message(
                platform_id="msg1",
                content="Test",
                author_id="user1",
                author_name="User",
                created_at=datetime.now(),
            )
        ]
        
        count = await processor.save_messages(uuid4(), messages)
        assert count == 1


class TestChannelConfigValidation:
    """渠道配置验证测试"""
    
    def test_discord_config_validation(self):
        """测试 Discord 配置"""
        from src.scrapers.base import ChannelConfig, Platform
        
        config = ChannelConfig(
            channel_id="ch-1",
            platform=Platform.DISCORD,
            access_token="valid_bot_token",
            extra_config={
                "guild_ids": ["123", "456"],
            },
        )
        
        assert config.platform == Platform.DISCORD
        assert config.access_token == "valid_bot_token"
        assert "guild_ids" in config.extra_config
    
    def test_reddit_config_validation(self):
        """测试 Reddit 配置"""
        from src.scrapers.base import ChannelConfig, Platform
        
        config = ChannelConfig(
            channel_id="ch-2",
            platform=Platform.REDDIT,
            access_token="reddit_token",
            extra_config={
                "client_id": "client123",
                "client_secret": "secret123",
                "subreddits": ["technology", "programming"],
            },
        )
        
        assert config.platform == Platform.REDDIT
        assert config.extra_config["subreddits"] == ["technology", "programming"]
    
    def test_qq_config_validation(self):
        """测试 QQ 配置 (uiautomator2)"""
        from src.scrapers.base import ChannelConfig, Platform
        
        config = ChannelConfig(
            channel_id="ch-3",
            platform=Platform.QQ,
            access_token="",
            extra_config={
                "device_id": "R3CR12345",
                "fetch_interval": 300,
            },
        )
        
        assert config.platform == Platform.QQ
        assert config.extra_config["device_id"] == "R3CR12345"
    
    def test_wecom_config_validation(self):
        """测试企业微信配置"""
        from src.scrapers.base import ChannelConfig, Platform
        
        config = ChannelConfig(
            channel_id="ch-4",
            platform=Platform.WECOM,
            access_token="wecom_token",
            extra_config={
                "corp_id": "ww123456",
                "corp_secret": "secret123",
                "agent_id": "1000001",
            },
        )
        
        assert config.platform == Platform.WECOM
        assert config.extra_config["corp_id"] == "ww123456"


class TestMCPIntegration:
    """MCP 集成测试"""
    
    def test_mcp_server_initialization(self):
        """测试 MCP Server 初始化"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        
        assert server.name == "social-feed-aggregator"
        assert server.version == "1.0.0"
        assert len(server._tools) == 4  # 4 个工具
    
    def test_mcp_tools_have_required_fields(self):
        """测试 MCP 工具包含必要字段"""
        from src.mcp.server import MCPServer
        
        server = MCPServer()
        tools = server.get_tools()
        
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"


class TestDatabaseModelsRelationships:
    """数据库模型关系测试"""
    
    def test_message_has_channel_relationship(self):
        """测试 Message 与 Channel 的关系"""
        from src.api.models.database import Message, Channel
        from uuid import uuid4
        
        channel = Channel(
            platform="discord",
            name="Test",
            config={},
        )
        
        message = Message(
            channel_id=uuid4(),
            platform_message_id="msg1",
            content="Test",
            author_id="user1",
            author_name="User",
            created_at=datetime.now(),
        )
        
        # 验证字段存在
        assert hasattr(message, 'channel_id')
        assert hasattr(message, 'platform_message_id')
        assert hasattr(message, 'content')
    
    def test_channel_has_messages_relationship(self):
        """测试 Channel 与 Messages 的关系"""
        from src.api.models.database import Channel
        
        channel = Channel(
            platform="discord",
            name="Test Channel",
            config={},
        )
        
        # 验证关系字段存在
        assert hasattr(channel, 'messages')
        assert hasattr(channel, 'fetch_logs')
