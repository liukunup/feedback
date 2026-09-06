"""
Scraper 基础接口定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import asyncio


class Platform(str, Enum):
    """支持的平台"""
    DISCORD = "discord"
    REDDIT = "reddit"
    QQ = "qq"
    WECOM = "wecom"


@dataclass
class Message:
    """统一的消息格式"""
    platform_id: str                    # 平台消息 ID
    content: str                         # 消息内容
    author_id: str                       # 作者 ID
    author_name: str                     # 作者名称
    created_at: datetime                # 创建时间 (必须在默认值字段之前)
    author_avatar: Optional[str] = None # 作者头像
    metadata: Dict[str, Any] = field(default_factory=dict)  # 原始元数据
    attachments: List[Dict[str, Any]] = field(default_factory=list)  # 附件
    channel_name: Optional[str] = None  # 频道/群组名称
    channel_id: Optional[str] = None   # 频道/群组 ID
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "platform_message_id": self.platform_id,
            "content": self.content,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "author_avatar": self.author_avatar,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "attachments": self.attachments,
            "channel_name": self.channel_name,
            "channel_id": self.channel_id,
        }


@dataclass
class ChannelConfig:
    """渠道配置"""
    channel_id: str                      # 内部渠道 ID (UUID)
    platform: Platform                   # 平台类型
    access_token: str                    # 访问令牌
    refresh_token: Optional[str] = None  # 刷新令牌
    extra_config: Dict[str, Any] = field(default_factory=dict)  # 额外配置


class BaseScraper(ABC):
    """Scraper 基类"""
    
    platform: Platform = Platform.DISCORD  # 子类需要重写
    
    def __init__(self):
        self._config: Optional[ChannelConfig] = None
        self._initialized: bool = False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @abstractmethod
    async def initialize(self, config: ChannelConfig) -> None:
        """初始化连接
        
        Args:
            config: 渠道配置
            
        Raises:
            AuthenticationError: 认证失败
            ScraperError: 其他初始化错误
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭连接，清理资源"""
        pass
    
    @abstractmethod
    async def fetch_messages(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
        channel_filter: Optional[str] = None
    ) -> List[Message]:
        """抓取消息
        
        Args:
            since: 只获取指定时间之后的消息
            limit: 最大消息数量
            channel_filter: 频道/群组过滤
            
        Returns:
            消息列表
            
        Raises:
            ScraperError: 抓取失败
            RateLimitError: API 限流
        """
        pass
    
    @abstractmethod
    async def verify_connection(self) -> bool:
        """验证连接是否正常
        
        Returns:
            连接是否有效
        """
        pass
    
    async def setup_webhook(self, callback_url: str) -> str:
        """设置 Webhook (可选实现)
        
        Args:
            callback_url: 回调地址
            
        Returns:
            Webhook ID
        """
        raise NotImplementedError(f"{self.platform} 不支持 Webhook")
    
    async def remove_webhook(self, webhook_id: str) -> None:
        """移除 Webhook (可选实现)
        
        Args:
            webhook_id: Webhook ID
        """
        raise NotImplementedError(f"{self.platform} 不支持 Webhook")
    
    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """获取频道信息 (可选实现)
        
        Args:
            channel_id: 频道 ID
            
        Returns:
            频道信息字典
        """
        raise NotImplementedError(f"{self.platform} 不支持获取频道信息")
    
    def _handle_rate_limit(self, retry_after: int) -> None:
        """处理限流
        
        Args:
            retry_after: 等待秒数
        """
        import logging
        logging.warning(f"Rate limited, waiting {retry_after} seconds")
        # 在子类中可以重写以实现自动重试


class ScraperRegistry:
    """Scraper 注册表"""
    
    _scrapers: Dict[Platform, type[BaseScraper]] = {}
    
    @classmethod
    def register(cls, platform: Platform):
        """注册 Scraper"""
        def decorator(scraper_class: type[BaseScraper]):
            cls._scrapers[platform] = scraper_class
            scraper_class.platform = platform
            return scraper_class
        return decorator
    
    @classmethod
    def get_scraper(cls, platform: Platform) -> BaseScraper:
        """获取 Scraper 实例"""
        if platform not in cls._scrapers:
            raise ValueError(f"Unknown platform: {platform}")
        return cls._scrapers[platform]()
    
    @classmethod
    def list_platforms(cls) -> List[Platform]:
        """列出所有支持的平台"""
        return list(cls._scrapers.keys())
