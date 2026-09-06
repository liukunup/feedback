# Social Feed Aggregator

多渠道社交媒体数据抓取和聚合服务

## 功能特性

- 🌐 **多渠道支持**: Discord, Reddit, QQ, 企业微信
- 📊 **数据聚合**: 统一展示不同平台的消息
- 🔍 **智能搜索**: 支持多条件筛选和全文搜索
- 🤖 **AI 分析**: 自动情感分析、标签提取、关键信息提取
- 🔌 **MCP 集成**: 支持 AI Agent 通过 MCP 协议搜索
- 🐳 **Docker 部署**: 一键启动所有服务

## 项目结构

```
social-feed-aggregator/
├── src/
│   ├── api/              # FastAPI 主服务
│   │   ├── main.py       # 应用入口
│   │   ├── models/       # 数据模型
│   │   └── routers/      # API 路由
│   ├── workers/          # Celery Worker
│   │   ├── tasks.py      # 任务定义
│   │   └── processors/   # 处理器
│   ├── scrapers/         # 渠道抓取器
│   │   ├── discord/
│   │   ├── reddit/
│   │   ├── qq/
│   │   └── wecom/
│   ├── mcp/              # MCP Server
│   ├── scheduler/         # 定时任务
│   └── core/              # 核心配置
├── webui/                   # React 前端
│   └── src/
├── docker/                # Docker 配置
├── migrations/            # 数据库迁移
└── tests/                 # 测试
```

## 快速开始

### 1. 环境要求

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 2. 配置

```bash
# 复制环境变量配置
cp .env.example .env

# 编辑 .env 文件，填入你的配置
```

主要配置项:
- `DB_PASSWORD`: 数据库密码
- `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`: AI 分析 API Key
- 各平台 (Discord/Reddit/QQ/企业微信) 的认证凭据

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api
```

### 4. 访问

- **Web UI**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 开发

### 后端

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行 API 服务
uvicorn src.api.main:app --reload --port 8000

# 运行 Worker
celery -A src.workers.tasks worker --loglevel=info

# 运行定时任务调度器
celery -A src.workers.tasks beat --loglevel=info
```

### 前端

```bash
cd web

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build
```

### 数据库迁移

```bash
# 应用迁移
psql -h localhost -U app -d social_feed -f migrations/001_initial.sql
```

## API 文档

### 渠道管理

```
POST   /api/channels/           # 创建渠道
GET    /api/channels/           # 列出渠道
GET    /api/channels/{id}       # 获取渠道详情
PATCH  /api/channels/{id}       # 更新渠道
DELETE /api/channels/{id}       # 删除渠道
POST   /api/channels/{id}/fetch # 手动触发抓取
```

### 消息查询

```
GET    /api/messages/           # 列出消息
GET    /api/messages/{id}       # 消息详情
DELETE /api/messages/{id}       # 删除消息
```

### 搜索

```
POST   /api/search/             # 搜索消息
GET    /api/search/stats        # 统计信息
GET    /api/search/categories   # 标签列表
```

### MCP

```
GET    /api/mcp/tools            # 列出可用工具
POST   /api/mcp/call            # 调用工具
```

## MCP 集成

在 AI Agent 中使用:

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
- `search_messages`: 搜索消息
- `get_message_detail`: 获取消息详情
- `get_channel_summary`: 渠道统计
- `list_channels`: 渠道列表

## 许可证

MIT
