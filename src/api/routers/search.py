"""
搜索 API
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..models.database import Message, Channel
from ..models.schemas import (
    SearchQuery, SearchResponse, StatisticsResponse,
    MessageResponse
)
from ...core.database import get_db

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/", response_model=SearchResponse)
async def search_messages(
    data: SearchQuery,
    db: AsyncSession = Depends(get_db),
):
    """搜索消息 (全文搜索 + 过滤)"""
    stmt = select(Message).join(Channel).where(Message.is_deleted == False)
    
    # 全文搜索
    if data.query:
        stmt = stmt.where(
            or_(
                Message.content.ilike(f"%{data.query}%"),
                Message.author_name.ilike(f"%{data.query}%"),
                Message.channel_name.ilike(f"%{data.query}%"),
            )
        )
    
    # 渠道过滤
    if data.channel_ids:
        stmt = stmt.where(Message.channel_id.in_(data.channel_ids))
    
    # 平台过滤
    if data.platforms:
        stmt = stmt.where(Channel.platform.in_(data.platforms))
    
    # 标签过滤
    if data.categories:
        for cat in data.categories:
            stmt = stmt.where(Message.categories.contains([cat]))
    
    # 情感过滤
    if data.sentiment:
        stmt = stmt.where(Message.sentiment == data.sentiment)
    
    # 作者过滤
    if data.author:
        stmt = stmt.where(Message.author_name.ilike(f"%{data.author}%"))
    
    # 时间范围
    if data.since:
        stmt = stmt.where(Message.created_at >= data.since)
    
    if data.until:
        stmt = stmt.where(Message.created_at <= data.until)
    
    # 计数
    count_stmt = select(func.count(Message.id))
    count_stmt = stmt.where(Message.is_deleted == False)
    
    total = await db.scalar(count_stmt)
    
    # 排序
    if data.sort_by == "relevance" and data.query:
        # 按相关性排序 (简化版: 按内容匹配度)
        stmt = stmt.order_by(Message.created_at.desc())
    else:
        if data.sort_order == "asc":
            stmt = stmt.order_by(getattr(Message, data.sort_by).asc())
        else:
            stmt = stmt.order_by(getattr(Message, data.sort_by).desc())
    
    # 分页
    offset = (data.page - 1) * data.page_size
    stmt = stmt.options(joinedload(Message.channel))
    stmt = stmt.offset(offset).limit(data.page_size)
    
    result = await db.execute(stmt)
    messages = result.scalars().unique().all()
    
    items = []
    for msg in messages:
        item = MessageResponse.model_validate(msg)
        if hasattr(msg, 'channel') and msg.channel:
            item.platform = msg.channel.platform
        items.append(item)
    
    # 聚合统计 (facets)
    facets = await _get_search_facets(db, stmt, data)
    
    return SearchResponse(
        query=data.query,
        total=total or 0,
        page=data.page,
        page_size=data.page_size,
        items=items,
        facets=facets,
    )


async def _get_search_facets(
    db: AsyncSession,
    base_stmt,
    data: SearchQuery,
) -> dict:
    """获取搜索聚合统计"""
    facets = {
        "platforms": {},
        "sentiments": {},
        "categories": {},
    }
    
    # 平台分布
    platform_stmt = select(
        Channel.platform,
        func.count(Message.id)
    ).join(
        Message, Message.channel_id == Channel.id
    ).where(Message.is_deleted == False)
    
    if data.channel_ids:
        platform_stmt = platform_stmt.where(Message.channel_id.in_(data.channel_ids))
    if data.since:
        platform_stmt = platform_stmt.where(Message.created_at >= data.since)
    if data.until:
        platform_stmt = platform_stmt.where(Message.created_at <= data.until)
    
    platform_stmt = platform_stmt.group_by(Channel.platform)
    
    platform_result = await db.execute(platform_stmt)
    for platform, count in platform_result.all():
        facets["platforms"][platform.value] = count
    
    # 情感分布
    sentiment_stmt = select(
        Message.sentiment,
        func.count(Message.id)
    ).where(Message.is_deleted == False)
    
    if data.channel_ids:
        sentiment_stmt = sentiment_stmt.where(Message.channel_id.in_(data.channel_ids))
    if data.since:
        sentiment_stmt = sentiment_stmt.where(Message.created_at >= data.since)
    if data.until:
        sentiment_stmt = sentiment_stmt.where(Message.created_at <= data.until)
    
    sentiment_stmt = sentiment_stmt.group_by(Message.sentiment)
    
    sentiment_result = await db.execute(sentiment_stmt)
    for sentiment, count in sentiment_result.all():
        if sentiment:
            facets["sentiments"][sentiment.value] = count
    
    return facets


@router.get("/stats", response_model=StatisticsResponse)
async def get_statistics(
    channel_id: Optional[UUID] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取统计信息"""
    # 基础条件
    conditions = [Message.is_deleted == False]
    if channel_id:
        conditions.append(Message.channel_id == channel_id)
    if since:
        conditions.append(Message.created_at >= since)
    if until:
        conditions.append(Message.created_at <= until)
    
    # 总消息数
    total_stmt = select(func.count(Message.id)).where(and_(*conditions))
    total_messages = await db.scalar(total_stmt) or 0
    
    # 总渠道数
    total_channels = await db.scalar(select(func.count(Channel.id)).where(Channel.enabled == True)) or 0
    
    # 按平台统计
    platform_stmt = select(
        Channel.platform,
        func.count(Message.id)
    ).join(
        Message, Message.channel_id == Channel.id
    ).where(and_(*conditions)).group_by(Channel.platform)
    
    platform_result = await db.execute(platform_stmt)
    messages_by_platform = {row[0].value: row[1] for row in platform_result.all()}
    
    # 按情感统计
    sentiment_stmt = select(
        Message.sentiment,
        func.count(Message.id)
    ).where(and_(*conditions)).group_by(Message.sentiment)
    
    sentiment_result = await db.execute(sentiment_stmt)
    messages_by_sentiment = {}
    for sentiment, count in sentiment_result.all():
        if sentiment:
            messages_by_sentiment[sentiment.value] = count
    
    # Top 标签
    # PostgreSQL 数组展开查询
    from sqlalchemy import text
    
    top_cat_stmt = text("""
        SELECT unnest(categories) as category, COUNT(*) as cnt
        FROM messages
        WHERE is_deleted = false
        AND categories IS NOT NULL
        AND categories != '{}'
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT 20
    """)
    
    cat_result = await db.execute(top_cat_stmt)
    top_categories = [
        {"category": row[0], "count": row[1]}
        for row in cat_result.all()
    ]
    
    # 今日消息
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_stmt = select(func.count(Message.id)).where(
        and_(*conditions, Message.created_at >= today_start)
    )
    messages_today = await db.scalar(today_stmt) or 0
    
    # 本周消息
    week_start = today_start - timedelta(days=today_start.weekday())
    week_stmt = select(func.count(Message.id)).where(
        and_(*conditions, Message.created_at >= week_start)
    )
    messages_this_week = await db.scalar(week_stmt) or 0
    
    return StatisticsResponse(
        total_messages=total_messages,
        total_channels=total_channels,
        messages_by_platform=messages_by_platform,
        messages_by_sentiment=messages_by_sentiment,
        top_categories=top_categories,
        messages_today=messages_today,
        messages_this_week=messages_this_week,
    )


@router.get("/categories")
async def list_categories(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """获取所有标签列表"""
    from sqlalchemy import text
    
    stmt = text("""
        SELECT unnest(categories) as category, COUNT(*) as cnt
        FROM messages
        WHERE is_deleted = false
        AND categories IS NOT NULL
        AND categories != '{}'
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT :limit
    """)
    
    result = await db.execute(stmt, {"limit": limit})
    
    return {
        "categories": [
            {"name": row[0], "count": row[1]}
            for row in result.all()
        ]
    }
