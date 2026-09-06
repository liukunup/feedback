"""
定时任务调度器
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.models.database import Channel, Message, FetchLog, FetchStatus
from ..core.database import async_session_maker
from ..scrapers.base import ScraperRegistry, Platform

logger = logging.getLogger(__name__)


class FetchScheduler:
    """抓取调度器"""
    
    def __init__(self):
        self._running = False
        self._tasks: List = []
    
    async def start(self):
        """启动调度器"""
        self._running = True
        logger.info("Fetch scheduler started")
    
    async def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("Fetch scheduler stopped")
    
    async def run_fetch_cycle(self):
        """执行一次抓取周期"""
        if not self._running:
            return
        
        async with async_session_maker() as session:
            # 获取所有启用的渠道
            result = await session.execute(
                select(Channel).where(Channel.enabled == True)
            )
            channels = result.scalars().all()
            
            for channel in channels:
                try:
                    await self._fetch_channel(session, channel)
                except Exception as e:
                    logger.error(f"Failed to fetch channel {channel.id}: {e}")
                    await self._log_fetch_failure(session, channel.id, str(e))
            
            await session.commit()
    
    async def _fetch_channel(self, session: AsyncSession, channel: Channel):
        """抓取单个渠道"""
        from ..scrapers.base import ChannelConfig
        from ..workers.processors.storage import StorageProcessor
        
        # 创建抓取日志
        fetch_log = FetchLog(
            channel_id=channel.id,
            status=FetchStatus.SUCCESS,
            started_at=datetime.utcnow(),
        )
        session.add(fetch_log)
        await session.flush()
        
        try:
            # 获取 scraper
            scraper = ScraperRegistry.get_scraper(Platform(channel.platform.value))
            
            # 构建配置
            config = ChannelConfig(
                channel_id=str(channel.id),
                platform=Platform(channel.platform.value),
                access_token=channel.config.get("access_token", ""),
                refresh_token=channel.config.get("refresh_token"),
                extra_config=channel.config,
            )
            
            # 初始化并抓取
            await scraper.initialize(config)
            
            # 计算抓取时间范围 (最近 24 小时)
            since = datetime.utcnow() - timedelta(hours=24)
            messages = await scraper.fetch_messages(since=since, limit=100)
            
            # 存储消息
            storage = StorageProcessor(session)
            new_count = await storage.save_messages(channel.id, messages)
            
            # 更新日志
            fetch_log.messages_count = len(messages)
            fetch_log.new_messages_count = new_count
            fetch_log.completed_at = datetime.utcnow()
            
            await scraper.close()
            
            logger.info(
                f"Fetched {len(messages)} messages ({new_count} new) "
                f"from channel {channel.name}"
            )
            
        except Exception as e:
            fetch_log.status = FetchStatus.FAILED
            fetch_log.error_message = str(e)
            fetch_log.completed_at = datetime.utcnow()
            raise
    
    async def _log_fetch_failure(
        self, 
        session: AsyncSession, 
        channel_id: UUID,
        error: str
    ):
        """记录抓取失败"""
        fetch_log = FetchLog(
            channel_id=channel_id,
            status=FetchStatus.FAILED,
            error_message=error,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        session.add(fetch_log)
        await session.flush()


# 全局调度器实例
scheduler = FetchScheduler()
