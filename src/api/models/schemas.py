"""
Pydantic Schemas
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ============ 平台枚举 ============
class Platform(str, Enum):
    DISCORD = "discord"
    REDDIT = "reddit"
    QQ = "qq"
    WECOM = "wecom"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


# ============ Channel Schemas ============
class ChannelBase(BaseModel):
    platform: Platform
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    enabled: bool = True


class ChannelCreate(ChannelBase):
    config: dict = Field(..., description="渠道特定配置")


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    enabled: Optional[bool] = None


class ChannelResponse(ChannelBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    webhook_id: Optional[str] = None
    webhook_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages_count: Optional[int] = None


class ChannelListResponse(BaseModel):
    total: int
    items: List[ChannelResponse]


# ============ Message Schemas ============
class MessageBase(BaseModel):
    content: str
    sentiment: Optional[Sentiment] = None
    categories: Optional[List[str]] = None
    entities: Optional[dict] = None
    summary: Optional[str] = None


class MessageResponse(MessageBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    channel_id: UUID
    platform_message_id: str
    author_id: str
    author_name: str
    author_avatar: Optional[str] = None
    created_at: datetime
    channel_name: Optional[str] = None
    metadata: Optional[dict] = None
    attachments: Optional[List[dict]] = None
    analyzed: bool
    platform: Optional[Platform] = None


class MessageListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[MessageResponse]


class MessageDetailResponse(MessageResponse):
    """消息详情，包含上下文"""
    previous_message: Optional[MessageResponse] = None
    next_message: Optional[MessageResponse] = None


# ============ Search Schemas ============
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    channel_ids: Optional[List[UUID]] = None
    platforms: Optional[List[Platform]] = None
    categories: Optional[List[str]] = None
    sentiment: Optional[Sentiment] = None
    author: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")  # created_at, relevance
    sort_order: str = Field(default="desc")  # asc, desc


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    items: List[MessageResponse]
    facets: Optional[dict] = None  # 聚合统计


# ============ Fetch Log Schemas ============
class FetchLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    channel_id: UUID
    status: str
    messages_count: int
    new_messages_count: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


# ============ Statistics Schemas ============
class StatisticsResponse(BaseModel):
    total_messages: int
    total_channels: int
    messages_by_platform: dict[str, int]
    messages_by_sentiment: dict[str, int]
    top_categories: List[dict]  # [{category: "xxx", count: 10}]
    messages_today: int
    messages_this_week: int


# ============ MCP Schemas ============
class MCPSearchParams(BaseModel):
    query: str
    channel: Optional[str] = None  # "all", "discord", "reddit", etc.
    categories: Optional[List[str]] = None
    sentiment: Optional[Sentiment] = None
    author: Optional[str] = None
    since: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)


class MCPMessageResult(BaseModel):
    id: str
    platform: str
    channel_name: str
    author_name: str
    content: str
    sentiment: Optional[str] = None
    categories: List[str]
    created_at: str
    url: Optional[str] = None
