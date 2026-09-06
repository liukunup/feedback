# 开发指南

本文档涵盖本地调试、打包发布和 Docker 部署的完整指南。

---

## 目录

- [环境准备](#环境准备)
- [本地开发](#本地开发)
- [调试](#调试)
- [测试](#测试)
- [打包](#打包)
- [Docker 部署](#docker-部署)

---

## 环境准备

### 系统要求

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (前端开发)
- PostgreSQL 16 (本地开发可选)
- Redis 7 (本地开发可选)

### 安装依赖

```bash
# 克隆项目
git clone <repo-url>
cd social-feed-aggregator

# 创建虚拟环境 (推荐)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\activate   # Windows

# 安装后端依赖 (含开发工具)
pip install -e ".[dev]"

# 安装前端依赖 (如需)
cd web && npm install
```

### 环境变量配置

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的 API Keys：

```env
# ============ 数据库 ============
DB_PASSWORD=your_secure_password
DATABASE_URL=postgresql+asyncpg://app:your_password@localhost:5432/social_feed

# ============ Redis ============
REDIS_URL=redis://localhost:6379

# ============ AI API (二选一) ============
OPENAI_API_KEY=sk-xxxx
# ANTHROPIC_API_KEY=sk-ant-xxxx

# ============ 安全 ============
SECRET_KEY=generate-a-secure-random-string-here
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# ============ 平台配置 ============
DISCORD_BOT_TOKEN=your_discord_bot_token
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
QQ_WS_URL=ws://localhost:5700
QQ_DEVICE_ID=R3CR12345
WECOM_CORP_ID=wwxxxx
WECOM_CORP_SECRET=xxxx
WECOM_AGENT_ID=1000001
```

---

## 本地开发

### 启动后端服务

```bash
# 终端 1: API 服务 (热重载)
uvicorn src.api.main:app --reload --port 8000

# 终端 2: Celery Worker (异步任务)
celery -A src.workers.tasks worker --loglevel=info

# 终端 3: Celery Beat (定时任务调度器)
celery -A src.workers.tasks beat --loglevel=info
```

服务地址：
- API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 启动前端服务

```bash
cd web

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

### 数据库迁移

```bash
# 使用 Docker 运行迁移
docker exec -it social_feed_postgres psql -U app -d social_feed -f /docker-entrypoint-initdb.d/001_initial.sql

# 或者本地运行
psql -h localhost -U app -d social_feed -f migrations/001_initial.sql
```

---

## 调试

### VS Code 调试配置

创建 `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.api.main:app",
        "--reload",
        "--port",
        "8000",
        "--host",
        "0.0.0.0"
      ],
      "justMyCode": true,
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Celery Worker",
      "type": "python",
      "request": "launch",
      "module": "celery",
      "args": [
        "-A", "src.workers.tasks",
        "worker",
        "--loglevel=info",
        "--concurrency=4"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Celery Beat",
      "type": "python",
      "request": "launch",
      "module": "celery",
      "args": [
        "-A", "src.workers.tasks",
        "beat",
        "--loglevel=info"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest: 当前文件",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "${file}",
        "-v",
        "-s"
      ],
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest: 所有测试",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-v",
        "--tb=short"
      ],
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm 调试配置

1. **Run > Edit Configurations**
2. 添加 Python 配置：
   - Script path: `uvicorn`
   - Parameters: `src.api.main:app --reload --port 8000`
   - Environment: `PYTHONPATH=<项目根目录>`
   - Working directory: `<项目根目录>`

3. 添加 Celery Worker：
   - Script path: `celery`
   - Parameters: `-A src.workers.tasks worker --loglevel=info`
   - Environment: `PYTHONPATH=<项目根目录>`

### 日志调试

```python
import logging

# 在代码中添加日志
logger = logging.getLogger(__name__)

logger.info("Info message")
logger.debug("Debug message: %s", variable)
logger.error("Error: %s", error)
```

查看实时日志：

```bash
# 本地服务日志
uvicorn src.api.main:app --reload --log-level debug

# Docker 日志
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f beat

# 查看特定时间段的日志
docker-compose logs --since 2024-01-01T00:00:00 api
```

### 数据库调试

```bash
# 连接数据库
docker exec -it social_feed_postgres psql -U app -d social_feed

# 常用命令
\dt              # 列出所有表
\d messages      # 查看表结构
\di              # 查看索引

# 调试查询
EXPLAIN ANALYZE SELECT * FROM messages WHERE channel_id = 'xxx';
```

---

## 测试

### 运行测试

```bash
# 运行所有测试
python -m pytest -v

# 运行带覆盖率报告
python -m pytest --cov=src --cov-report=html --cov-report=term

# 运行特定测试文件
python -m pytest tests/test_api.py -v

# 运行特定测试类
python -m pytest tests/test_api.py::TestHealthEndpoint -v

# 运行特定测试函数
python -m pytest tests/test_api.py::TestHealthEndpoint::test_health_check -v

# 只运行失败的测试
python -m pytest --lf

# 在第一个失败时停止
python -m pytest -x
```

### 测试覆盖的模块

| 测试文件 | 覆盖范围 |
|---------|---------|
| `test_api.py` | API 路由、Schema 验证、配置 |
| `test_app.py` | FastAPI 应用初始化 |
| `test_exceptions.py` | 异常类定义和转换 |
| `test_integration.py` | Scraper 集成、消息解析 |
| `test_mcp_server.py` | MCP Server 工具定义和执行 |
| `test_schemas.py` | Pydantic Schema 验证 |
| `test_scrapers.py` | Scraper 基类和配置 |

### 编写新测试

```python
# tests/test_example.py
import pytest
from datetime import datetime

class TestExample:
    """测试示例"""
    
    def test_basic(self):
        """基础测试"""
        assert 1 + 1 == 2
    
    @pytest.mark.asyncio
    async def test_async(self):
        """异步测试"""
        import asyncio
        result = await asyncio.sleep(0.1)
        assert result is None
    
    def test_with_fixture(self, tmp_path):
        """使用 fixture"""
        assert tmp_path.exists()
    
    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_parametrized(self, input, expected):
        """参数化测试"""
        assert input * 2 == expected
```

### Mock 使用

```python
from unittest.mock import Mock, AsyncMock, patch

def test_with_mock():
    """使用同步 Mock"""
    mock_obj = Mock()
    mock_obj.method.return_value = "mocked"
    
    result = mock_obj.method()
    assert result == "mocked"

@pytest.mark.asyncio
async def test_with_async_mock():
    """使用异步 Mock"""
    mock_db = AsyncMock()
    mock_db.execute.return_value = AsyncMock()
    
    # 使用 mock
    result = await mock_db.execute("SELECT 1")
```

---

## 打包

### Python 包发布

```bash
# 1. 安装构建工具
pip install build twine

# 2. 更新版本号 (pyproject.toml)
# version = "1.0.0"

# 3. 构建包
python -m build

# 4. 发布到 TestPyPI (测试)
twine upload --repository testpypi dist/*

# 5. 发布到 PyPI (正式)
twine upload dist/*

# 6. 验证安装
pip install --index-url https://test.pypi.org/simple/ social-feed-aggregator
```

### Docker 镜像构建

```bash
# 构建所有镜像
docker build -f docker/Dockerfile.api -t social-feed-api:latest .
docker build -f docker/Dockerfile.worker -t social-feed-worker:latest .
docker build -f docker/Dockerfile.beat -t social-feed-beat:latest .

# 带版本号
docker build -f docker/Dockerfile.api \
  -t social-feed-api:1.0.0 \
  -t social-feed-api:latest \
  .

# 多架构构建 (可选)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t social-feed-api:latest \
  --push \
  -f docker/Dockerfile.api \
  .

# 构建时传入变量
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VERSION=1.0.0 \
  -f docker/Dockerfile.api \
  -t social-feed-api:latest \
  .
```

### 镜像优化

Dockerfile 优化技巧：

```dockerfile
# 使用多阶段构建
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src/ ./src/
ENV PATH=/root/.local/bin:$PATH

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0"]
```

---

## Docker 部署

### 快速启动

```bash
# 方式 1: 使用启动脚本
./start.sh up           # 启动所有服务
./start.sh down        # 停止所有服务
./start.sh restart     # 重启
./start.sh logs        # 查看日志
./start.sh status      # 服务状态
./start.sh build       # 重新构建镜像
./start.sh shell       # 进入 API 容器
./start.sh db          # 进入数据库

# 方式 2: 直接使用 docker-compose
docker-compose up -d              # 后台启动
docker-compose ps                 # 查看状态
docker-compose logs -f            # 查看所有日志
docker-compose logs -f api        # 只看 API 日志
docker-compose logs -f worker     # 只看 Worker 日志
docker-compose down               # 停止
docker-compose down -v           # 停止并删除数据卷
```

### 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                       │
│                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
│  │   Nginx     │   │    API      │   │   Worker    │ │
│  │  (端口 80)  │──▶│ (端口 8000) │──▶│  (Celery)  │ │
│  └─────────────┘   └─────────────┘   └──────┬──────┘ │
│                                               │         │
│  ┌─────────────┐   ┌─────────────┐   ┌──────▼──────┐ │
│  │    Redis    │◀──│    Beat     │   │   Worker    │ │
│  │  (端口 6379)│   │ (定时任务)  │   │  (Celery)   │ │
│  └─────────────┘   └─────────────┘   └─────────────┘ │
│                                                         │
│  ┌─────────────┐                                       │
│  │ PostgreSQL  │                                       │
│  │  (端口 5432)│                                       │
│  │  + pgvector │                                       │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

### 服务说明

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | pgvector/pgvector:pg16 | 5432 | PostgreSQL + 向量扩展 |
| redis | redis:7-alpine | 6379 | 缓存和消息队列 |
| api | Dockerfile.api | 8000 | FastAPI 主服务 |
| worker | Dockerfile.worker | - | 异步任务处理 |
| beat | Dockerfile.beat | - | 定时任务调度 |

### 访问地址

| 服务 | 地址 |
|------|------|
| Web UI | http://localhost:3000 |
| API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| ReDoc | http://localhost:8000/redoc |

### 环境变量配置

创建 `.env` 文件：

```env
# 必须配置
DB_PASSWORD=your_secure_password

# 可选配置
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key
SECRET_KEY=your-32-char-secret-key
```

### 服务扩缩容

```bash
# 扩展 Worker 数量
docker-compose up -d --scale worker=3

# 查看扩展后的服务
docker-compose ps

# 动态调整日志级别
docker-compose exec api python -c "import logging; logging.getLogger().setLevel(logging.DEBUG)"
```

### 数据管理

```bash
# 备份数据库
docker exec social_feed_postgres pg_dump -U app social_feed > backup.sql

# 恢复数据库
docker exec -i social_feed_postgres psql -U app social_feed < backup.sql

# 清理未使用的镜像
docker image prune -f

# 清理所有未使用资源
docker system prune -a -f
```

### 生产部署检查清单

- [ ] 修改默认密码 (`DB_PASSWORD`, `SECRET_KEY`)
- [ ] 配置 SSL/TLS 证书
- [ ] 设置正确的 `ALLOWED_ORIGINS`
- [ ] 配置日志持久化
- [ ] 设置数据库备份策略
- [ ] 配置资源限制 (CPU/内存)
- [ ] 启用监控和告警

### 生产环境配置示例

```yaml
# docker-compose.prod.yml
services:
  api:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - PYTHONENV=production
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

启动生产环境：

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 常见问题

### 1. 数据库连接失败

```bash
# 检查数据库是否运行
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 等待数据库就绪
docker-compose exec postgres pg_isready -U app -d social_feed
```

### 2. Worker 无法连接 Redis

```bash
# 检查 Redis
docker-compose exec redis redis-cli ping

# 应该返回: PONG
```

### 3. 端口被占用

```bash
# 查找占用端口的进程
lsof -i :8000
lsof -i :5432
lsof -i :6379

# 停止占用进程或修改 docker-compose.yml 中的端口映射
```

### 4. 清理重建

```bash
# 完全重置 (删除所有数据)
docker-compose down -v
docker system prune -f
docker-compose up -d --build
```

---

## 相关文档

- [README.md](./README.md) - 项目简介
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 架构设计
- [QUICKSTART.md](./QUICKSTART.md) - 快速入门
