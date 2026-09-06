#!/bin/bash
# ============ 启动所有服务 ============

set -e

echo "Starting Social Feed Aggregator (All-in-One)..."

# 等待 Redis 和 PostgreSQL 就绪
echo "Waiting for database..."
sleep 5

# 运行数据库迁移
echo "Running database migrations..."
python -c "
from src.core.database import init_db
import asyncio
asyncio.run(init_db())
" 2>/dev/null || echo "Migrations skipped (may already exist)"

# 启动所有服务 (后台运行)
echo "Starting API server..."
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting Celery Worker..."
celery -A src.workers.tasks worker --loglevel=info --concurrency=4 &
WORKER_PID=$!

echo "Starting Celery Beat (scheduler)..."
celery -A src.workers.tasks beat --loglevel=info &
BEAT_PID=$!

echo ""
echo "All services started!"
echo "  API:     http://localhost:8000"
echo "  Docs:    http://localhost:8000/docs"
echo "  Worker:  PID $WORKER_PID"
echo "  Beat:    PID $BEAT_PID"
echo ""

# 等待任意服务退出
wait $API_PID $WORKER_PID $BEAT_PID
