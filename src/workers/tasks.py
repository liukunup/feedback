"""
Celery Worker 任务定义
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from celery import Celery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import async_session_maker
from ..scrapers.base import ScraperRegistry, Message, Platform
from .processors.analyzers.openai_analyzer import MessageAnalyzer
from .processors.storage import StorageProcessor

settings = get_settings()

# 创建 Celery 应用
celery_app = Celery(
    "social_feed_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 分钟超时
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


# ============ 抓取任务 ============

@celery_app.task(bind=True, name="fetch_channel")
def fetch_channel(self, channel_id: str, platform: str) -> dict:
    """抓取单个渠道的消息
    
    Args:
        channel_id: 渠道 UUID
        platform: 平台类型 (discord, reddit, qq, wecom)
    """
    # 创建新的事件循环来运行异步代码
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_fetch_channel_async(str(channel_id), platform))
        return result
    finally:
        loop.close()


async def _fetch_channel_async(channel_id: str, platform: str) -> dict:
    """异步抓取渠道消息"""
    from ..api.models.database import Channel, FetchLog, FetchStatus
    
    async with async_session_maker() as session:
        # 获取渠道配置
        result = await session.execute(
            select(Channel).where(Channel.id == UUID(channel_id))
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            return {"status": "error", "message": "Channel not found"}
        
        if not channel.enabled:
            return {"status": "skipped", "message": "Channel disabled"}
        
        # 创建抓取日志
        fetch_log = FetchLog(
            channel_id=channel.id,
            status=FetchStatus.SUCCESS,
            started_at=datetime.utcnow(),
        )
        session.add(fetch_log)
        
        try:
            # 获取 scraper
            scraper = ScraperRegistry.get_scraper(Platform(platform))
            
            # 构建配置（解密敏感字段）
            config_dict = channel.config or {}
            from ..core.encryption import decrypt_token
            from ..scrapers.base import ChannelConfig
            config = ChannelConfig(
                channel_id=str(channel.id),
                platform=Platform(platform),
                access_token=decrypt_token(config_dict.get("access_token", "")),
                refresh_token=decrypt_token(config_dict.get("refresh_token")) if config_dict.get("refresh_token") else None,
                extra_config=config_dict,
            )
            
            # 初始化 scraper
            await scraper.initialize(config)
            
            # 抓取消息 (获取最近 24 小时)
            since = datetime.utcnow() - timedelta(hours=24)
            messages = await scraper.fetch_messages(since=since, limit=100)
            
            # 存储消息
            storage = StorageProcessor(session)
            new_count = await storage.save_messages(channel.id, messages)
            
            # 更新抓取日志
            fetch_log.messages_count = len(messages)
            fetch_log.new_messages_count = new_count
            fetch_log.status = FetchStatus.SUCCESS
            fetch_log.completed_at = datetime.utcnow()
            
            await session.commit()
            
            # 触发分析任务
            for msg in messages[:10]:  # 限制队列长度
                analyze_message.delay(str(channel.id), msg.platform_id)
            
            await scraper.close()
            
            return {
                "status": "success",
                "channel_id": str(channel.id),
                "total_messages": len(messages),
                "new_messages": new_count,
            }
            
        except Exception as e:
            logging.error(f"Fetch failed for channel {channel_id}: {e}")
            fetch_log.status = FetchStatus.FAILED
            fetch_log.error_message = str(e)
            fetch_log.completed_at = datetime.utcnow()
            await session.commit()
            
            return {
                "status": "error",
                "channel_id": str(channel.id),
                "error": str(e),
            }


@celery_app.task(name="fetch_all_channels")
def fetch_all_channels() -> dict:
    """抓取所有启用的渠道"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_fetch_all_channels_async())
    finally:
        loop.close()


async def _fetch_all_channels_async() -> dict:
    """异步抓取所有渠道"""
    from ..api.models.database import Channel
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Channel).where(Channel.enabled == True)
        )
        channels = result.scalars().all()
        
        results = []
        for channel in channels:
            result = _fetch_channel_async.delay(str(channel.id), channel.platform.value)
            results.append({
                "channel_id": str(channel.id),
                "task_id": result.id,
            })
        
        return {
            "total_channels": len(channels),
            "tasks": results,
        }


# ============ 分析任务 ============

@celery_app.task(bind=True, name="analyze_message")
def analyze_message(self, channel_id: str, platform_message_id: str) -> dict:
    """分析单条消息
    
    Args:
        channel_id: 渠道 ID
        platform_message_id: 平台消息 ID
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze_message_async(channel_id, platform_message_id))
    finally:
        loop.close()


async def _analyze_message_async(channel_id: str, platform_message_id: str) -> dict:
    """异步分析消息"""
    from ..api.models.database import Message, AnalysisTask
    
    async with async_session_maker() as session:
        # 查找消息
        result = await session.execute(
            select(Message).where(
                Message.channel_id == UUID(channel_id),
                Message.platform_message_id == platform_message_id,
            )
        )
        message = result.scalar_one_or_none()
        
        if not message:
            return {"status": "error", "message": "Message not found"}
        
        if message.analyzed:
            return {"status": "skipped", "message": "Already analyzed"}
        
        # 创建分析任务
        task = AnalysisTask(
            message_id=message.id,
            status="processing",
        )
        session.add(task)
        await session.flush()
        
        try:
            analyzer = MessageAnalyzer()
            
            # 分析消息
            result = await analyzer.analyze(message.content)
            
            # 更新消息
            message.sentiment = result.sentiment
            message.categories = result.categories
            message.entities = result.entities
            message.summary = result.summary
            message.analyzed = True
            
            # 更新任务
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "status": "success",
                "message_id": str(message.id),
                "sentiment": result.sentiment.value if result.sentiment else None,
                "categories": result.categories,
            }
            
        except Exception as e:
            logging.error(f"Analysis failed for message {platform_message_id}: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.retry_count += 1
            await session.commit()
            
            # 重试
            if task.retry_count < 3:
                analyze_message.apply_async(
                    args=[channel_id, platform_message_id],
                    countdown=60 * task.retry_count,  # 1, 2, 3 分钟
                )
            
            return {
                "status": "error",
                "message_id": str(message.id),
                "error": str(e),
            }


@celery_app.task(name="analyze_pending_messages")
def analyze_pending_messages(limit: int = 100) -> dict:
    """批量分析待处理消息"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze_pending_messages_async(limit))
    finally:
        loop.close()


async def _analyze_pending_messages_async(limit: int = 100) -> dict:
    """异步批量分析"""
    from ..api.models.database import Message, AnalysisTask
    
    async with async_session_maker() as session:
        # 查找未分析的消息
        result = await session.execute(
            select(Message)
            .where(Message.analyzed == False)
            .where(Message.content.isnot(None))
            .where(Message.content != "")
            .limit(limit)
        )
        messages = result.scalars().all()
        
        # 创建分析任务
        for message in messages:
            task = AnalysisTask(
                message_id=message.id,
                status="pending",
            )
            session.add(task)
        
        await session.commit()
        
        # 触发分析任务
        for message in messages:
            analyze_message.delay(
                str(message.channel_id),
                message.platform_message_id
            )
        
        return {
            "queued_messages": len(messages),
        }


# ============ 清理任务 ============

@celery_app.task(bind=True, name="cleanup_old_analysis_tasks")
def cleanup_old_analysis_tasks(self, days: int = 30) -> dict:
    """清理旧的分析任务记录"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup_old_tasks_async(days))
    finally:
        loop.close()


async def _cleanup_old_tasks_async(days: int) -> dict:
    """异步清理任务"""
    from ..api.models.database import AnalysisTask
    
    async with async_session_maker() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = await session.execute(
            select(func.count(AnalysisTask.id))
            .where(AnalysisTask.completed_at < cutoff)
        )
        count = result.scalar()
        
        # 删除旧记录
        await session.execute(
            AnalysisTask.__table__.delete()
            .where(AnalysisTask.completed_at < cutoff)
        )
        
        await session.commit()
        
        return {"deleted_count": count}


# ============ 周期任务配置 ============

celery_app.conf.beat_schedule = {
    "fetch-all-channels-every-5-minutes": {
        "task": "fetch_all_channels",
        "schedule": 300.0,  # 5 分钟
    },
    "analyze-pending-messages": {
        "task": "analyze_pending_messages",
        "schedule": 60.0,  # 1 分钟
    },
    "cleanup-old-tasks-daily": {
        "task": "cleanup_old_analysis_tasks",
        "schedule": 86400.0,  # 1 天
    },
}
