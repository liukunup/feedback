#!/bin/bash
# ============ 启动完整服务 (API + Worker + Frontend) ============

set -e

echo "Starting Social Feed Aggregator (Full Stack)..."

# 等待 Redis 和 PostgreSQL 就绪
echo "Waiting for database..."
for i in {1..30}; do
    nc -z localhost 5432 && break || sleep 1
done

# 运行数据库迁移
echo "Running database migrations..."
python -c "
from src.core.database import init_db
import asyncio
asyncio.run(init_db())
" 2>/dev/null || echo "Migrations skipped"

# 启动所有服务
echo "Starting API server..."
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting Celery Worker..."
celery -A src.workers.tasks worker --loglevel=info --concurrency=4 &
WORKER_PID=$!

echo "Starting Celery Beat..."
celery -A src.workers.tasks beat --loglevel=info &
BEAT_PID=$!

echo "Starting Nginx..."
nginx &

echo ""
echo "All services started!"
echo "  Frontend: http://localhost"
echo "  API:     http://localhost:8000"
echo "  Docs:    http://localhost:8000/docs"
echo ""

# 等待任意服务退出
wait $API_PID $WORKER_PID $BEAT_PID
