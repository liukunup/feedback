# Social Feed Aggregator - 架构设计文档

## 1. 项目概述

**项目名称**: Social Feed Aggregator (社交信息聚合器)

**核心功能**: 
- 多渠道社交媒体数据抓取（只读模式）
- AI 驱动的消息分析与标签化
- Web 端聚合展示与 MCP 搜索能力

**技术栈选择**:
- **语言**: Python 3.11+ (抓取服务) + TypeScript/React (前端)
- **数据库**: PostgreSQL 16 (支持向量搜索)
- **消息队列**: Redis (任务队列与缓存)
- **容器**: Docker + Docker Compose
- **AI**: OpenAI API / Claude API (消息分析)

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              整体架构                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Discord   │    │   Reddit    │    │     QQ      │    │  企业微信    │  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│         │                  │                  │                  │         │
│         └──────────────────┴────────┬─────────┴──────────────────┘         │
│                                      │                                      │
│                         ┌────────────▼────────────┐                        │
│                         │     抓取调度器 (Scheduler)   │                        │
│                         │  • 定时任务              │                        │
│                         │  • Webhook 事件接收      │                        │
│                         └────────────┬────────────┘                        │
│                                      │                                      │
│                         ┌────────────▼────────────┐                        │
│                         │      消息队列 (Redis)     │                        │
│                         │  • Celery Worker        │                        │
│                         └────────────┬────────────┘                        │
│                                      │                                      │
│         ┌────────────────────────────┼────────────────────────────┐       │
│         │                            │                            │       │
│         ▼                            ▼                            ▼       │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐     │
│  │  存储服务    │            │  AI 分析服务 │            │  MCP 服务    │     │
│  │  (PostgreSQL)│           │  (标签/关键信息)│          │  (搜索能力)  │     │
│  └──────┬──────┘            └──────┬──────┘            └──────┬──────┘     │
│         │                           │                           │          │
│         └───────────────────────────┼───────────────────────────┘          │
│                                     │                                       │
│                         ┌───────────▼───────────┐                          │
│                         │    Web 前端展示       │                          │
│                         │  • 渠道切换          │                          │
│                         │  • 消息浏览          │                          │
│                         │  • 搜索筛选          │                          │
│                         └───────────────────────┘                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块设计

### 3.1 项目结构

```
social-feed-aggregator/
├── docker/
│   ├── Dockerfile.api          # API 服务镜像
│   ├── Dockerfile.worker        # Worker 镜像
│   └── Dockerfile.web          # Web 前端镜像
│
├── src/
│   ├── api/                    # FastAPI 主服务
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── messages.py     # 消息查询 API
│   │   │   ├── channels.py     # 渠道管理 API
│   │   │   └── search.py       # 搜索 API
│   │   ├── models/             # Pydantic 模型
│   │   └── dependencies.py
│   │
│   ├── workers/                # Celery Worker
│   │   ├── tasks.py            # 任务定义
│   │   └── processors/
│   │       ├── fetcher.py      # 统一抓取接口
│   │       ├── analyzers/
│   │       │   └── openai_analyzer.py
│   │       └── storage.py      # 存储接口
│   │
│   ├── scrapers/               # 各渠道抓取器
│   │   ├── base.py             # 基类
│   │   ├── discord/
│   │   ├── reddit/
│   │   ├── qq/
│   │   └── wecom/              # 企业微信
│   │
│   ├── mcp/                    # MCP Server 实现
│   │   ├── server.py
│   │   └── tools.py            # 搜索工具定义
│   │
│   ├── scheduler/              # 定时调度
│   │   └── jobs.py
│   │
│   └── core/                   # 核心配置
│       ├── config.py
│       ├── database.py
│       └── exceptions.py
│
├── web/                        # React 前端
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── services/
│   └── package.json
│
├── migrations/                  # 数据库迁移
│
├── tests/
│
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### 3.2 数据库设计

```sql
-- 渠道配置表
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL,      -- discord, reddit, qq, wecom
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,              -- 渠道特定配置(加密存储)
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES channels(id),
    
    -- 原始信息
    platform_message_id VARCHAR(255) NOT NULL,
    content TEXT,
    author_id VARCHAR(255),
    author_name VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    
    -- 元数据
    metadata JSONB,                     -- 原始 JSON
    attachments JSONB,
    
    -- AI 分析结果
    sentiment VARCHAR(50),              -- positive, neutral, negative
    categories TEXT[],                  -- 标签数组
    entities JSONB,                     -- 提取的实体 {users: [], orgs: [], topics: []}
    embedding VECTOR(1536),             -- 向量嵌入
    
    -- 状态
    analyzed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_messages_channel_id ON messages(channel_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_messages_author ON messages(author_id, author_name);
CREATE INDEX idx_messages_categories ON messages USING GIN(categories);

-- 全文搜索索引
CREATE INDEX idx_messages_content_fts ON messages USING GIN(to_tsvector('chinese', content));

-- 向量相似度搜索
CREATE INDEX idx_messages_embedding ON messages USING IVFFlat(embedding vector_cosine_ops);

-- 抓取记录表
CREATE TABLE fetch_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES channels(id),
    status VARCHAR(20),                 -- success, failed, partial
    messages_count INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

---

## 4. 渠道适配器设计

### 4.1 统一接口

```python
# src/scrapers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Message:
    platform_id: str
    content: str
    author_id: str
    author_name: str
    created_at: datetime
    metadata: dict
    attachments: List[dict]

@dataclass
class ChannelConfig:
    channel_id: str
    access_token: str
    refresh_token: Optional[str]
    extra_config: dict

class BaseScraper(ABC):
    platform: str = "unknown"
    
    @abstractmethod
    async def initialize(self, config: ChannelConfig) -> None:
        """初始化连接"""
        pass
    
    @abstractmethod
    async def fetch_messages(
        self, 
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Message]:
        """抓取消息"""
        pass
    
    @abstractmethod
    async def setup_webhook(self, callback_url: str) -> str:
        """设置 Webhook 返回 webhook_id"""
        pass
    
    @abstractmethod
    async def remove_webhook(self, webhook_id: str) -> None:
        """移除 Webhook"""
        pass
```

### 4.2 各渠道实现要点

#### Discord
- **推荐方式**: discord.py 库 + Bot Token
- 事件订阅: `MESSAGE_CREATE`, `MESSAGE_UPDATE`
- WebSocket Gateway 自动重连
- 缓存机制避免重复获取

#### Reddit
- 使用 Reddit API (PRAW 库)
- OAuth2 认证
- 监听 subreddit 或用户

#### QQ
- **推荐方式**: uiautomator2 + 手机端
  - USB/WiFi 连接 Android 手机
  - 模拟用户操作获取消息
  - 备选: go-cqhttp WebSocket

#### 企业微信
- 使用企业微信应用消息回调
- 接收用户消息事件
- 需要公网可访问的 Webhook URL

---

## 5. AI 分析服务

```python
# src/workers/processors/analyzers/openai_analyzer.py
from enum import Enum
from typing import List

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

@dataclass
class AnalysisResult:
    sentiment: Sentiment
    categories: List[str]          # ["产品反馈", "Bug报告", "功能建议"]
    entities: dict                  # {"users": [], "orgs": ["公司A"], "topics": []}
    summary: str

class MessageAnalyzer:
    SYSTEM_PROMPT = """你是一个社交媒体消息分析助手。
分析用户消息并提取:
1. 情感倾向 (positive/neutral/negative)
2. 分类标签 (最多5个)
3. 关键实体 (提到的用户、组织、主题)
4. 简短摘要 (50字内)"""

    async def analyze(self, message_content: str) -> AnalysisResult:
        # 调用 LLM API
        # 可选: 使用 embedding 进行向量化
        pass
```

---

## 6. MCP 服务设计

```python
# src/mcp/server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import httpx

app = Server("social-feed-aggregator")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_messages",
            description="搜索社交媒体消息",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "channel": {"type": "string", "enum": ["all", "discord", "reddit", "qq", "wecom"]},
                    "categories": {"type": "array", "items": {"type": "string"}},
                    "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                    "author": {"type": "string"},
                    "since": {"type": "string", "format": "date-time"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        Tool(
            name="get_message_context",
            description="获取消息的上下文(前后消息)",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_messages":
        return await search_messages(**arguments)
    # ...
```

---

## 7. Web 前端设计

```
┌─────────────────────────────────────────────────────────────────┐
│  Social Feed Aggregator                              [设置] [?] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  渠道: [全部] [Discord] [Reddit] [QQ] [企业微信]                 │
│                                                                 │
│  筛选: [标签 ▼] [情感 ▼] [时间范围 ▼] [🔍 搜索...]               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📱 Discord - #general                          2小时前  │   │
│  │ @用户A: 这产品用起来真不错，就是加载有点慢 👎             │   │
│  │        标签: [产品反馈] [性能问题]  情感: 😐             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📘 Reddit - r/feedback                          5小时前  │   │
│  │ u/用户B: 希望增加暗黑模式功能，建议参考 XXX 方案         │   │
│  │        标签: [功能建议] [UI/UX]    情感: 😊             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 💬 QQ - 反馈群                                    昨天   │   │
│  │ 用户C: 登录一直失败，什么情况？                        │   │
│  │        标签: [Bug报告]              情感: 😟           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Docker 部署

### docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL + pgvector
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: social_feed
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # API 服务
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    environment:
      DATABASE_URL: postgresql+asyncpg://app:${DB_PASSWORD}@postgres:5432/social_feed
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  # Worker 服务
  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    environment:
      DATABASE_URL: postgresql+asyncpg://app:${DB_PASSWORD}@postgres:5432/social_feed
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis

  # Web 前端
  web:
    build:
      context: ./web
      dockerfile: ../docker/Dockerfile.web
    ports:
      - "3000:80"
    depends_on:
      - api

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - api
      - web

volumes:
  postgres_data:
```

---

## 9. 环境变量配置

```env
# .env.example

# 数据库
DB_PASSWORD=your_secure_password
DATABASE_URL=postgresql+asyncpg://app:password@localhost:5432/social_feed

# Redis
REDIS_URL=redis://localhost:6379

# API Keys
OPENAI_API_KEY=sk-...
# 或
ANTHROPIC_API_KEY=sk-ant-...

# 渠道配置 (加密存储)
DISCORD_BOT_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
QQ_WS_URL=ws://localhost:5700
WECOM_CORP_ID=
WECOM_CORP_SECRET=
WECOM_WEBHOOK_TOKEN=

# 安全
SECRET_KEY=your_random_secret_key
ALLOWED_ORIGINS=http://localhost:3000

# Webhook 回调地址 (公网)
WEBHOOK_BASE_URL=https://your-public-domain.com
```

---

## 10. 实现优先级

### Phase 1: MVP (4-6 周)
1. ✅ 项目脚手架 + Docker 化
2. ✅ PostgreSQL 数据库 + 迁移
3. ✅ 一个渠道抓取器 (Discord 最佳，API 完善)
4. ✅ 基础 API 服务
5. ✅ 简单 Web 展示页面

### Phase 2: 核心功能 (2-3 周)
6. ✅ 剩余渠道适配器
7. ✅ AI 分析服务集成
8. ✅ 定时任务 + Webhook
9. ✅ 消息搜索功能

### Phase 3: MCP 集成 (1-2 周)
10. ✅ MCP Server 实现
11. ✅ Agent 集成测试

### Phase 4: 优化
12. ✅ 性能优化 (缓存、批处理)
13. ✅ 监控告警
14. ✅ 单元/集成测试

---

## 11. 风险与注意事项

| 风险 | 缓解措施 |
|------|----------|
| API 限流 | 实现指数退避、请求队列 |
| 数据量增长 | 分表、定期归档历史数据 |
| 渠道 API 变更 | 适配器模式隔离变化 |
| 敏感信息泄露 | 渠道配置加密、密钥轮换 |
| 公网 Webhook | HTTPS + 签名验证 |

---

需要我进一步细化某个模块的实现细节，或者开始搭建项目脚手架吗？
