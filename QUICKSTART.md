# 快速开始

## 方式一: Docker 一键启动 (推荐)

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd social-feed-aggregator

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Keys

# 3. 启动
./start.sh up

# 4. 访问
open http://localhost:3000
```

## 方式二: 本地开发

### 后端

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置数据库
# 使用 Docker 运行 PostgreSQL
docker run -d \
  --name social_feed_db \
  -e POSTGRES_DB=social_feed \
  -e POSTGRES_USER=app \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 4. 初始化数据库
psql -h localhost -U app -d social_feed -f migrations/001_initial.sql

# 5. 启动 API
uvicorn src.api.main:app --reload --port 8000

# 6. 启动 Worker (新终端)
celery -A src.workers.tasks worker --loglevel=info
```

### 前端

```bash
cd web

# 安装依赖
npm install

# 开发模式
npm run dev

# 或构建生产版本
npm run build
```

## 配置说明

### .env 文件

```env
# 数据库
DB_PASSWORD=your_password
DATABASE_URL=postgresql+asyncpg://app:password@localhost:5432/social_feed

# AI (二选一)
OPENAI_API_KEY=sk-...

# 渠道配置
DISCORD_BOT_TOKEN=your_bot_token
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
```

### QQ 抓取配置

**方式 1: 手机 uiautomator2**
```bash
# 1. 连接 Android 手机并启用 USB 调试
adb devices

# 2. 安装 uiautomator2
pip install uiautomator2
python -m uiautomator2 install

# 3. 配置
echo "QQ_DEVICE_ID=$(adb devices | grep device | head -1 | awk '{print $1}')" >> .env
```

**方式 2: go-cqhttp WebSocket**
```env
QQ_WS_URL=ws://localhost:5700
QQ_ACCESS_TOKEN=your_token
```

## API 使用

### 创建渠道

```bash
curl -X POST http://localhost:8000/api/channels/ \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "discord",
    "name": "My Discord Server",
    "config": {"access_token": "your_bot_token"}
  }'
```

### 触发抓取

```bash
curl -X POST http://localhost:8000/api/channels/{channel_id}/fetch
```

### 搜索消息

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "产品反馈",
    "platforms": ["discord", "reddit"],
    "sentiment": "positive"
  }'
```

## MCP 集成

在 Claude Desktop 或其他支持 MCP 的 Agent 中配置:

```json
{
  "mcpServers": {
    "social-feed": {
      "command": "python",
      "args": ["-m", "src.mcp.server"]
    }
  }
}
```

可用工具:
- `search_messages`: 搜索社交媒体消息
- `get_message_detail`: 获取消息详情
- `get_channel_summary`: 渠道统计
- `list_channels`: 列出所有渠道
