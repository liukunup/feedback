"""
FastAPI 主应用
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .routers import channels, messages, search
from ..mcp.server import mcp_router
from ..core.config import get_settings
from ..core.database import init_db, close_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info("Starting Social Feed Aggregator API...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # 关闭
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connection closed")


# 创建 FastAPI 应用
app = FastAPI(
    title="Social Feed Aggregator",
    description="多渠道社交媒体数据抓取和聚合服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# 注册路由
app.include_router(channels.router)
app.include_router(messages.router)
app.include_router(search.router)
app.include_router(mcp_router)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "social-feed-aggregator"}


@app.get("/")
async def root():
    return {
        "service": "Social Feed Aggregator",
        "version": "1.0.0",
        "docs": "/docs",
    }


# Webhook 回调端点 (供各渠道推送消息)
@app.post("/webhook/{channel_id}")
async def webhook_callback(
    channel_id: str,
    request: Request,
):
    """接收各渠道的 Webhook 回调"""
    from ..workers.tasks import fetch_channel
    
    try:
        body = await request.json()
        
        # 触发抓取任务
        # 这里应该根据 channel_id 查找对应的平台类型
        # 简化处理，实际应该从数据库获取
        task = fetch_channel.delay(channel_id, "unknown")
        
        return {"status": "received", "task_id": task.id}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


# 企业微信回调验证
@app.get("/webhook/wecom/verify")
async def wecom_verify(
    msg_signature: str,
    timestamp: str,
    nonce: str,
    echostr: str,
):
    """企业微信回调 URL 验证"""
    # TODO: 实现签名验证
    import base64
    try:
        return {"echostr": echostr}  # 返回解密后的内容
    except Exception:
        return {"error": "verify failed"}


@app.post("/webhook/wecom/callback")
async def wecom_callback(request: Request):
    """企业微信消息回调"""
    from ..workers.tasks import fetch_channel
    
    body = await request.body()
    
    # TODO: 解析并验证消息
    # 调用 fetch_channel 处理
    
    return {"status": "ok"}
