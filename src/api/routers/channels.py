"""
渠道管理 API
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import Channel, Platform
from ..models.schemas import (
    ChannelCreate, ChannelUpdate, ChannelResponse, ChannelListResponse
)
from ...core.database import get_db
from ...core.exceptions import ChannelNotFoundError
from ...core.encryption import encrypt_token

router = APIRouter(prefix="/channels", tags=["Channels"])


# 需要加密的字段
SENSITIVE_FIELDS = ['access_token', 'refresh_token', 'api_key', 'api_secret', 'client_secret']


@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建新渠道"""
    # 验证平台
    try:
        platform = Platform(data.platform.value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform: {data.platform}"
        )
    
    # 加密敏感配置
    config = data.config or {}
    for field in SENSITIVE_FIELDS:
        if field in config and config[field]:
            config[field] = encrypt_token(str(config[field]))
    
    channel = Channel(
        platform=platform,
        name=data.name,
        description=data.description,
        config=config,
        enabled=data.enabled,
    )
    
    db.add(channel)
    await db.flush()
    await db.refresh(channel)
    
    return channel


@router.get("/", response_model=ChannelListResponse)
async def list_channels(
    platform: Optional[str] = None,
    enabled: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取渠道列表"""
    stmt = select(Channel)
    
    # 过滤
    if platform:
        try:
            platform_enum = Platform(platform)
            stmt = stmt.where(Channel.platform == platform_enum)
        except ValueError:
            pass
    
    if enabled is not None:
        stmt = stmt.where(Channel.enabled == enabled)
    
    # 计数
    count_stmt = select(func.count(Channel.id))
    if platform:
        count_stmt = count_stmt.where(Channel.platform == Platform(platform))
    if enabled is not None:
        count_stmt = count_stmt.where(Channel.enabled == enabled)
    
    total = await db.scalar(count_stmt)
    
    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Channel.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    channels = result.scalars().all()
    
    return ChannelListResponse(
        total=total or 0,
        items=[ChannelResponse.model_validate(ch) for ch in channels],
    )


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取渠道详情"""
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    return channel


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: UUID,
    data: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新渠道"""
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    
    # 如果更新 config，需要加密敏感字段
    if 'config' in update_data and update_data['config']:
        for field in SENSITIVE_FIELDS:
            if field in update_data['config'] and update_data['config'][field]:
                update_data['config'][field] = encrypt_token(str(update_data['config'][field]))
    
    for field, value in update_data.items():
        setattr(channel, field, value)
    
    await db.flush()
    await db.refresh(channel)
    
    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除渠道"""
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    await db.delete(channel)
    await db.flush()


@router.post("/{channel_id}/enable", response_model=ChannelResponse)
async def enable_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """启用渠道"""
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    channel.enabled = True
    await db.flush()
    await db.refresh(channel)
    
    return channel


@router.post("/{channel_id}/disable", response_model=ChannelResponse)
async def disable_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """禁用渠道"""
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    channel.enabled = False
    await db.flush()
    await db.refresh(channel)
    
    return channel


@router.post("/{channel_id}/fetch")
async def trigger_fetch(
    channel_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """手动触发抓取"""
    from ...workers.tasks import fetch_channel
    
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # 触发异步任务
    task = fetch_channel.delay(str(channel_id), channel.platform.value)
    
    return {
        "task_id": task.id,
        "status": "queued",
        "channel_id": str(channel_id),
    }
