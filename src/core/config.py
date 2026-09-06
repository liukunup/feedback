"""
核心配置模块
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")
    """应用配置"""
    
    # 数据库
    database_url: str = "postgresql+asyncpg://app:password@localhost:5432/social_feed"
    db_password: Optional[str] = None  # 仅用于向后兼容，不使用
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Discord
    discord_bot_token: Optional[str] = None
    discord_http_proxy: Optional[str] = None   # Discord HTTP 代理
    discord_https_proxy: Optional[str] = None  # Discord HTTPS 代理
    
    # Reddit
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "SocialFeedAggregator/1.0"
    
    # QQ (uiautomator2)
    qq_device_id: Optional[str] = None  # 手机设备 ID (adb devices 中的 ID，如 R3CR12345)
    qq_auto_init: bool = True           # 自动初始化 uiautomator2
    
    # 企业微信
    wecom_corp_id: Optional[str] = None
    wecom_corp_secret: Optional[str] = None
    wecom_agent_id: Optional[str] = None
    
    # Webhook
    webhook_base_url: str = "http://localhost:8000"
    
    # 安全
    secret_key: str = "change-me-in-production"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    # 代理配置
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[str] = None

    # AI 分析
    ai_model: str = "gpt-4o-mini"
    ai_embedding_model: str = "text-embedding-3-small"
    ai_batch_size: int = 10
    
    # 任务配置
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # 抓取配置
    fetch_interval_seconds: int = 300  # 默认 5 分钟
    fetch_batch_size: int = 100
    max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
