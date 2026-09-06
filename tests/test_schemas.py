"""
Schema 验证测试
"""
import pytest
from datetime import datetime
from uuid import uuid4


class TestChannelSchemas:
    """测试渠道 Schema"""
    
    def test_channel_create_valid(self):
        """测试创建渠道 Schema 有效数据"""
        from src.api.models.schemas import ChannelCreate, Platform
        
        data = ChannelCreate(
            platform=Platform.DISCORD,
            name="Test Channel",
            description="A test channel",
            config={"token": "abc123"},
        )
        
        assert data.platform == Platform.DISCORD
        assert data.name == "Test Channel"
        assert data.description == "A test channel"
        assert data.config["token"] == "abc123"
        assert data.enabled == True
    
    def test_channel_create_without_description(self):
        """测试创建渠道 Schema 可选描述"""
        from src.api.models.schemas import ChannelCreate, Platform
        
        data = ChannelCreate(
            platform=Platform.REDDIT,
            name="Reddit Channel",
            config={},
        )
        
        assert data.description is None
    
    def test_channel_update_partial(self):
        """测试更新渠道 Schema 部分更新"""
        from src.api.models.schemas import ChannelUpdate
        
        data = ChannelUpdate(name="Updated Name")
        
        assert data.name == "Updated Name"
        assert data.description is None
        assert data.config is None
        assert data.enabled is None
    
    def test_channel_response_validation(self):
        """测试渠道响应 Schema"""
        from src.api.models.schemas import ChannelResponse, Platform
        
        channel_id = uuid4()
        now = datetime.now()
        
        data = ChannelResponse(
            id=channel_id,
            platform=Platform.DISCORD,
            name="Response Channel",
            config={},
            enabled=True,
            webhook_id="wh_123",
            created_at=now,
            updated_at=now,
        )
        
        assert data.id == channel_id
        assert data.webhook_id == "wh_123"


class TestMessageSchemas:
    """测试消息 Schema"""
    
    def test_message_response_complete(self):
        """测试消息响应 Schema 完整数据"""
        from src.api.models.schemas import MessageResponse, Platform, Sentiment
        
        msg_id = uuid4()
        channel_id = uuid4()
        now = datetime.now()
        
        data = MessageResponse(
            id=msg_id,
            channel_id=channel_id,
            platform_message_id="msg-123",
            content="Test message content",
            author_id="user-1",
            author_name="Test User",
            author_avatar="https://example.com/avatar.png",
            created_at=now,
            channel_name="general",
            metadata={"key": "value"},
            attachments=[{"type": "image", "url": "http://img.jpg"}],
            sentiment=Sentiment.POSITIVE,
            categories=["tech", "news"],
            entities={"users": ["john"], "orgs": ["company"]},
            summary="Short summary",
            analyzed=True,
            platform=Platform.DISCORD,
        )
        
        assert data.content == "Test message content"
        assert data.sentiment == Sentiment.POSITIVE
        assert data.analyzed == True
        assert len(data.categories) == 2
    
    def test_message_response_minimal(self):
        """测试消息响应 Schema 最少数据"""
        from src.api.models.schemas import MessageResponse
        
        msg_id = uuid4()
        channel_id = uuid4()
        now = datetime.now()
        
        data = MessageResponse(
            id=msg_id,
            channel_id=channel_id,
            platform_message_id="msg-456",
            content="Minimal message",
            author_id="user-2",
            author_name="Another User",
            created_at=now,
            analyzed=False,
        )
        
        assert data.content == "Minimal message"
        assert data.sentiment is None
        assert data.categories is None
    
    def test_message_list_response(self):
        """测试消息列表响应 Schema"""
        from src.api.models.schemas import MessageListResponse, MessageResponse
        
        msg_id = uuid4()
        channel_id = uuid4()
        now = datetime.now()
        
        items = [
            MessageResponse(
                id=msg_id,
                channel_id=channel_id,
                platform_message_id=f"msg-{i}",
                content=f"Message {i}",
                author_id="user",
                author_name="User",
                created_at=now,
                analyzed=False,
            )
            for i in range(3)
        ]
        
        data = MessageListResponse(
            total=100,
            page=1,
            page_size=20,
            items=items,
        )
        
        assert data.total == 100
        assert len(data.items) == 3


class TestSearchSchemas:
    """测试搜索 Schema"""
    
    def test_search_query_complete(self):
        """测试搜索查询 Schema 完整数据"""
        from src.api.models.schemas import SearchQuery, Platform, Sentiment
        
        data = SearchQuery(
            query="test search",
            channel_ids=[uuid4(), uuid4()],
            platforms=[Platform.DISCORD, Platform.REDDIT],
            categories=["tech"],
            sentiment=Sentiment.POSITIVE,
            author="John",
            since=datetime(2024, 1, 1),
            until=datetime(2024, 12, 31),
            page=2,
            page_size=50,
            sort_by="relevance",
            sort_order="asc",
        )
        
        assert data.query == "test search"
        assert len(data.channel_ids) == 2
        assert data.page == 2
        assert data.sort_by == "relevance"
    
    def test_search_query_minimal(self):
        """测试搜索查询 Schema 最少数据"""
        from src.api.models.schemas import SearchQuery
        
        data = SearchQuery(query="minimal search")
        
        assert data.query == "minimal search"
        assert data.page == 1
        assert data.page_size == 20
        assert data.sort_by == "created_at"
        assert data.sort_order == "desc"
    
    def test_search_query_validation_empty_query(self):
        """测试搜索查询空字符串验证"""
        from src.api.models.schemas import SearchQuery
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            SearchQuery(query="")
    
    def test_search_query_validation_query_too_long(self):
        """测试搜索查询字符串过长验证"""
        from src.api.models.schemas import SearchQuery
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            SearchQuery(query="x" * 501)
    
    def test_search_query_page_size_max(self):
        """测试搜索查询分页大小上限"""
        from src.api.models.schemas import SearchQuery
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            SearchQuery(query="test", page_size=101)
    
    def test_search_response(self):
        """测试搜索响应 Schema"""
        from src.api.models.schemas import SearchResponse, MessageResponse
        
        msg_id = uuid4()
        data = SearchResponse(
            query="test",
            total=42,
            page=1,
            page_size=20,
            items=[],
            facets={"platforms": {"discord": 20}},
        )
        
        assert data.total == 42
        assert data.facets["platforms"]["discord"] == 20


class TestStatisticsSchema:
    """测试统计 Schema"""
    
    def test_statistics_response(self):
        """测试统计响应 Schema"""
        from src.api.models.schemas import StatisticsResponse
        
        data = StatisticsResponse(
            total_messages=1000,
            total_channels=5,
            messages_by_platform={"discord": 600, "reddit": 400},
            messages_by_sentiment={"positive": 500, "neutral": 300, "negative": 200},
            top_categories=[
                {"category": "tech", "count": 100},
                {"category": "news", "count": 80},
            ],
            messages_today=50,
            messages_this_week=300,
        )
        
        assert data.total_messages == 1000
        assert data.messages_by_platform["discord"] == 600
        assert data.top_categories[0]["category"] == "tech"


class TestFetchLogSchema:
    """测试抓取日志 Schema"""
    
    def test_fetch_log_response(self):
        """测试抓取日志响应 Schema"""
        from src.api.models.schemas import FetchLogResponse
        
        log_id = uuid4()
        channel_id = uuid4()
        now = datetime.now()
        
        data = FetchLogResponse(
            id=log_id,
            channel_id=channel_id,
            status="success",
            messages_count=100,
            new_messages_count=10,
            error_message=None,
            started_at=now,
            completed_at=now,
        )
        
        assert data.status == "success"
        assert data.messages_count == 100
        assert data.new_messages_count == 10
        assert data.error_message is None


class TestMCPSchemas:
    """测试 MCP Schema"""
    
    def test_mcp_search_params(self):
        """测试 MCP 搜索参数 Schema"""
        from src.api.models.schemas import MCPSearchParams, Sentiment
        
        data = MCPSearchParams(
            query="mcp search",
            channel="discord",
            categories=["tech"],
            sentiment=Sentiment.POSITIVE,
            author="John",
            since=datetime(2024, 1, 1),
            limit=50,
        )
        
        assert data.query == "mcp search"
        assert data.channel == "discord"
        assert data.limit == 50
    
    def test_mcp_message_result(self):
        """测试 MCP 消息结果 Schema"""
        from src.api.models.schemas import MCPMessageResult
        
        data = MCPMessageResult(
            id="msg-123",
            platform="discord",
            channel_name="general",
            author_name="User",
            content="Test content",
            sentiment="positive",
            categories=["tech"],
            created_at="2024-01-01T12:00:00",
            url="https://discord.com/...",
        )
        
        assert data.id == "msg-123"
        assert data.sentiment == "positive"
        assert data.url is not None


class TestEnumConsistency:
    """测试枚举一致性"""
    
    def test_platform_enum_consistency(self):
        """测试平台枚举一致性"""
        from src.api.models.schemas import Platform as SchemaPlatform
        from src.scrapers.base import Platform as ScraperPlatform
        
        # 两个模块中的枚举值应该一致
        for p in SchemaPlatform:
            assert ScraperPlatform(p.value) is not None
    
    def test_sentiment_enum_consistency(self):
        """测试情感枚举一致性"""
        from src.api.models.schemas import Sentiment
        
        assert Sentiment.POSITIVE.value == "positive"
        assert Sentiment.NEUTRAL.value == "neutral"
        assert Sentiment.NEGATIVE.value == "negative"
