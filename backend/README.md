# 新闻看板后端 (News Board Backend)

FastAPI + APScheduler 新闻采集系统后端，提供 REST API 和定时采集调度。

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（开发模式，支持热重载）
python -m uvicorn backend.main:app --host 0.0.0.0 --port 3000 --reload

# 或直接运行
python backend/main.py
```

## 目录结构

```
backend/
├── main.py                 # FastAPI 入口 + APScheduler 调度器
├── api/                    # REST API 路由
│   ├── news.py             # 新闻接口
│   ├── rag.py              # RAG 接口
│   ├── auth.py             # 认证接口
│   ├── subscription.py    # 订阅接口
│   ├── feedback.py         # 反馈接口
│   └── config_api.py       # 配置接口
├── core/                   # 业务逻辑
│   └── news_service.py
├── script/                 # 数据管道
│   ├── bootstrap.py        # 统一路径管理（APP_ROOT=/app）
│   ├── db/                 # 数据库操作
│   │   ├── connection.py   # SQLite 连接池 + init_db()
│   │   ├── schema.sql      # 表结构定义
│   │   └── ...            # CRUD 模块
│   ├── crawl/              # 采集管道
│   ├── score/              # LLM 评分
│   ├── sector/             # 板块数据
│   ├── rag/                # RAG 报告生成
│   ├── service/            # 服务层（全量同步）
│   ├── llm/                # LLM 调用客户端
│   ├── log/                # 日志模块
│   └── config/             # 配置管理
└── requirements.txt
```

## 环境变量

在 `backend/.env`（或项目根目录 `.env`）中配置：

```env
# LLM 配置
MINIMAX_API_KEY=your_api_key_here
MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic
MINIMAX_MODEL=MiniMax-M2.7

# APP_ROOT（容器内为 /app，本地开发自动推断）
# APP_ROOT=/app
```

## 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/` | 服务信息 |
| POST | `/api/pipeline/run` | 手动触发新闻采集 |
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 更新配置 |
| GET/POST | `/api/news/*` | 新闻接口 |
| GET/POST | `/api/rag/*` | RAG 接口 |

## 数据库

- SQLite 数据库位于 `{APP_ROOT}/db/primary.db`
- 启动时自动调用 `init_db()` 检查并迁移表结构
- 支持 `ALTER TABLE ADD COLUMN` 增量迁移，不丢数据

## 核心标的知识库（RAG）

### 数据结构

| 表 | 用途 |
|---|---|
| `rag_sectors` | 板块名称 + 产业链覆盖情况 |
| `rag_stocks` | 核心标的（代码/名称/梯队/四维度/护城河等） |

### 更新核心标的

**单板块更新：**
```bash
python script/rag/generate_rag.py --sector "新能源汽车"
```

**批量更新（并行执行）：**
```bash
python script/rag/generate_rag_batch.py --sectors "半导体,AI视频,新能源汽车" --concurrency 3
```

### 工作流程

```
指定板块
  ↓
调用 LLM（基于 prompt/核心标的.md 的提示词）
  ↓
LLM 返回结构化报告文本（正文表格 + 3个附录）
  ↓
parser.py 解析报告 → 提取标的和产业链覆盖
  ↓
db/rag.py.save_all() 写入数据库（先删后插）
```

### 查询接口

| 方法 | 路径 | 说明 |
|---|---|
| GET | `/api/rag/sectors` | 查询所有板块 |
| GET | `/api/rag/stocks?sector=新能源汽车` | 按板块查询核心标的 |
| POST | `/api/rag/parse` | 解析报告入库 |

### 全量同步

将 `db.sectors` 表中的**所有板块**批量重新生成核心标的（每批3个板块并行，批间串行，日志输出到 `logs/auto_sync_sectors_rag_*.log`）：

```bash
python service/auto_sync_sectors_rag.py
```

### 高分新闻自动关联板块

将 `importance_score >= 8` 且无板块的新闻自动关联到已有板块：
```bash
python script/rag/auto_match_sectors.py
```

## 定时任务

| 任务 | 间隔 | 说明 |
|------|------|------|
| `news_pipeline` | 每 30 分钟 | 新闻采集全流程 |
| `sync_sector_values` | 每 1 小时 | 同步板块指数值 |

## 命令行脚本

```bash
# 新闻采集全流程
python -m script.crawl.crawler

# 单独运行各步骤
python -m script.crawl.list_crawler    # Step 1: 采集列表页
python -m script.crawl.news_filter     # Step 2: LLM 过滤
python -m script.crawl.article_crawler # Step 3: 采集正文

# 生成 RAG 报告
python script/rag/generate_rag.py --sector "新能源汽车"
python script/rag/generate_rag_batch.py --sectors "房地产,建筑装饰" --concurrency 3

# 全量同步所有板块的核心标的（生产级）
python service/auto_sync_sectors_rag.py

# 高分新闻自动关联板块
python script/rag/auto_match_sectors.py

# 同步板块数据
python script/sector/sync_sector_values.py
```

## Docker 部署

```bash
# 构建并启动
docker compose -f deploy/docker-compose.yml up -d --build

# 查看日志
docker compose -f deploy/docker-compose.yml logs -f

# 停止
docker compose -f deploy/docker-compose.yml down
```

容器内路径：`APP_ROOT=/app`，所有代码在 `/app/backend/`。