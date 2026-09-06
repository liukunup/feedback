"""
消息查询 API
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..models.database import Message, Channel
from ..models.schemas import (
    MessageResponse, MessageListResponse, MessageDetailResponse,
    Platform, Sentiment
)
from ...core.database import get_db

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("/", response_model=MessageListResponse)
async def list_messages(
    channel_id: Optional[UUID] = None,
    platform: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    author: Optional[str] = None,
    analyzed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取消息列表"""
    stmt = select(Message).join(Channel).where(Message.is_deleted == False)
    
    # 过滤条件
    if channel_id:
        stmt = stmt.where(Message.channel_id == channel_id)
    
    if platform:
        stmt = stmt.where(Channel.platform == platform)
    
    if sentiment:
        stmt = stmt.where(Message.sentiment == sentiment)
    
    if category:
        stmt = stmt.where(Message.categories.contains([category]))
    
    if since:
        stmt = stmt.where(Message.created_at >= since)
    
    if until:
        stmt = stmt.where(Message.created_at <= until)
    
    if author:
        stmt = stmt.where(Message.author_name.ilike(f"%{author}%"))
    
    if analyzed is not None:
        stmt = stmt.where(Message.analyzed == analyzed)
    
    # 计数
    count_stmt = select(func.count(Message.id))
    # 应用相同的过滤条件
    count_stmt = stmt.where(Message.is_deleted == False)
    if channel_id:
        count_stmt = count_stmt.where(Message.channel_id == channel_id)
    if platform:
        count_stmt = count_stmt.join(Channel).where(Channel.platform == platform)
    if sentiment:
        count_stmt = count_stmt.where(Message.sentiment == sentiment)
    if category:
        count_stmt = count_stmt.where(Message.categories.contains([category]))
    if since:
        count_stmt = count_stmt.where(Message.created_at >= since)
    if until:
        count_stmt = count_stmt.where(Message.created_at <= until)
    if author:
        count_stmt = count_stmt.where(Message.author_name.ilike(f"%{author}%"))
    if analyzed is not None:
        count_stmt = count_stmt.where(Message.analyzed == analyzed)
    
    total = await db.scalar(count_stmt)
    
    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.options(joinedload(Message.channel))
    stmt = stmt.order_by(Message.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    messages = result.scalars().unique().all()
    
    items = []
    for msg in messages:
        item = MessageResponse.model_validate(msg)
        if hasattr(msg, 'channel') and msg.channel:
            item.platform = msg.channel.platform
        items.append(item)
    
    return MessageListResponse(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{message_id}", response_model=MessageDetailResponse)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取消息详情"""
    stmt = select(Message).options(
        joinedload(Message.channel)
    ).where(Message.id == message_id)
    
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    response = MessageDetailResponse.model_validate(message)
    if hasattr(message, 'channel') and message.channel:
        response.platform = message.channel.platform
    
    # 获取上下文 (前后消息)
    # 上一条
    prev_stmt = select(Message).where(
        and_(
            Message.channel_id == message.channel_id,
            Message.created_at < message.created_at,
        )
    ).order_by(Message.created_at.desc()).limit(1)
    
    prev_result = await db.execute(prev_stmt)
    prev_message = prev_result.scalar_one_or_none()
    
    if prev_message:
        response.previous_message = MessageResponse.model_validate(prev_message)
    
    # 下一条
    next_stmt = select(Message).where(
        and_(
            Message.channel_id == message.channel_id,
            Message.created_at > message.created_at,
        )
    ).order_by(Message.created_at.asc()).limit(1)
    
    next_result = await db.execute(next_stmt)
    next_message = next_result.scalar_one_or_none()
    
    if next_message:
        response.next_message = MessageResponse.model_validate(next_message)
    
    return response


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """软删除消息"""
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    message.is_deleted = True
    await db.flush()
