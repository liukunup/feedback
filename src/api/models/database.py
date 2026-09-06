"""
数据库模型
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey, Index, JSON, ARRAY, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
# VECTOR 需要 pgvector 扩展，如不需要向量搜索可注释掉
# from sqlalchemy.dialects.postgresql import VECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from src.core.database import Base


class Platform(str, enum.Enum):
    """支持的平台"""
    DISCORD = "discord"
    REDDIT = "reddit"
    QQ = "qq"
    WECOM = "wecom"


class Sentiment(str, enum.Enum):
    """情感倾向"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class FetchStatus(str, enum.Enum):
    """抓取状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class Channel(Base):
    """渠道配置表"""
    __tablename__ = "channels"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 渠道特定配置 (加密存储)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Webhook 配置
    webhook_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # 状态
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # 关系
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="channel")
    fetch_logs: Mapped[List["FetchLog"]] = relationship("FetchLog", back_populates="channel")
    
    __table_args__ = (
        Index("idx_channels_platform", "platform"),
        Index("idx_channels_enabled", "enabled"),
    )


class Message(Base):
    """消息表"""
    __tablename__ = "messages"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    channel_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    
    # 原始信息
    platform_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 元数据 (使用 extra_metadata 避免与 SQLAlchemy 保留字冲突)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # 原始 JSON
    attachments: Mapped[Optional[List[dict]]] = mapped_column(JSONB, nullable=True)
    channel_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 如频道名、subreddit
    
    # AI 分析结果
    sentiment: Mapped[Optional[Sentiment]] = mapped_column(SQLEnum(Sentiment), nullable=True)
    categories: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    entities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {users: [], orgs: [], topics: []}
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSONB, nullable=True)  # 向量嵌入
    
    # 状态
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # 软删除
    
    # 关系
    channel: Mapped["Channel"] = relationship("Channel", back_populates="messages")
    
    __table_args__ = (
        Index("idx_messages_channel_id", "channel_id"),
        Index("idx_messages_created_at", "created_at"),
        Index("idx_messages_author", "author_id"),
        Index("idx_messages_platform_msg_id", "platform_message_id"),
        Index("idx_messages_analyzed", "analyzed"),
        # GIN 索引用于数组搜索
        Index("idx_messages_categories_gin", "categories", postgresql_using="gin"),
    )


class FetchLog(Base):
    """抓取日志表"""
    __tablename__ = "fetch_logs"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    channel_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    
    status: Mapped[FetchStatus] = mapped_column(SQLEnum(FetchStatus), nullable=False)
    messages_count: Mapped[int] = mapped_column(default=0)
    new_messages_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 关系
    channel: Mapped["Channel"] = relationship("Channel", back_populates="fetch_logs")
    
    __table_args__ = (
        Index("idx_fetch_logs_channel_id", "channel_id"),
        Index("idx_fetch_logs_started_at", "started_at"),
    )


class AnalysisTask(Base):
    """AI 分析任务表"""
    __tablename__ = "analysis_tasks"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed
    retry_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
