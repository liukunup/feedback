#!/bin/bash
# Social Feed Aggregator - 快速启动脚本

set -e

echo "=============================================="
echo "   Social Feed Aggregator - 启动脚本"
echo "=============================================="
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 检查配置文件
if [ ! -f .env ]; then
    echo "📝 创建 .env 配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件配置你的 API Keys"
fi

# Docker Compose 命令
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

# 处理参数
case "${1:-up}" in
    up)
        echo "🚀 启动所有服务..."
        $COMPOSE up -d
        echo ""
        echo "✅ 服务已启动!"
        echo ""
        echo "访问地址:"
        echo "  - Web UI:     http://localhost:3000"
        echo "  - API:        http://localhost:8000"
        echo "  - API Docs:   http://localhost:8000/docs"
        echo "  - Health:     http://localhost:8000/health"
        ;;
    down)
        echo "🛑 停止所有服务..."
        $COMPOSE down
        ;;
    restart)
        echo "🔄 重启所有服务..."
        $COMPOSE restart
        ;;
    logs)
        echo "📜 查看日志 (Ctrl+C 退出)..."
        $COMPOSE logs -f
        ;;
    status)
        echo "📊 服务状态:"
        $COMPOSE ps
        ;;
    build)
        echo "🔨 构建镜像..."
        $COMPOSE build --no-cache
        ;;
    shell)
        echo "🐚 进入 API 容器..."
        $COMPOSE exec api /bin/bash
        ;;
    db)
        echo "🗄️  进入数据库..."
        $COMPOSE exec postgres psql -U app social_feed
        ;;
    *)
        echo "用法: $0 {up|down|restart|logs|status|build|shell|db}"
        exit 1
        ;;
esac
