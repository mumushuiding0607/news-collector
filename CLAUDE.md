# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

- **所有脚本开头**：`from script.bootstrap import *`
- **数据库操作**：`from script.db import ...`（禁止直接调用 `get_conn()`）
- **表结构定义**：`backend/script/db/schema.sql`（唯一数据源）
- **板块归一化**：`from script.db import normalize`
- **RAG 工作流**：generate_rag → parser → rag.save_all()

## Code Rules

**通用**
- 一个功能一个模块，基础设施层统一实现，不重复
- 同类模块必须放在同一目录，禁止不同抽象层次混放
- 超出 200 行的文件必须拆分
- 函数单一职责，副作用集中在外层
- 模块间通过接口通信，不依赖具体实现
- 发现违反规则的代码，当场重构，不只是指出问题

**Python（后端）**
- 所有脚本开头：`from script.bootstrap import *`
- 数据库操作必须通过 `script.db` 模块，禁止直接调用 `get_conn()`
- 表结构定义在 `backend/script/db/schema.sql` 中，是唯一数据源
- 新增模块必须登记到 `backend/requirements.txt`
- log 文件在 `logs/` 目录，test 文件在 `test/` 目录

**Flutter（前端）**
- 组件通过 props/emit 或 store 通信，不直接依赖实现细节
- 业务层调用基础设施时，必须调用对应模块，不自行实现

## 常用命令

```bash
# ===== 后端服务 =====
cd backend
python main.py                              # 启动 FastAPI 服务（默认端口 31234）
python -m uvicorn backend.main:app --reload # 开发模式热重载

# ===== 数据库初始化 =====
cd backend
python -c "from script.db import init_db; init_db()"  # 初始化/迁移数据库表结构

# ===== 新闻采集（从项目根目录或 backend 目录均可）=====
python -m script.crawl.list_crawler           # 采集所有数据源列表页
python -m script.crawl.article_crawler        # 采集所有数据源正文
python -m script.crawl.list_crawler <url>     # 采集单个数据源

# ===== 统一学习（同时发现列表配置和正文配置）=====
python -m script.crawl.list_crawler --learn <url> [--title "标题样本"] [--name "数据源名称"] [--skip-article] [--force-relearn]

# 参数说明：
#   --learn <url>       启动学习模式（必填）
#   --title "标题"      已知标题，用于标题逆推定位新闻列表（可选）
#   --name "名称"       数据源名称（可选，默认使用 URL）
#   --skip-article      设置 list_complete=True，跳过正文抓取（可选）
#   --force-relearn     强制重新学习配置，覆盖已有配置（可选）

# 示例：
python -m script.crawl.list_crawler --learn https://www.csdn.net --title "某个已知标题" --name "CSDN资讯" --skip-article

# ===== 异动消息处理 =====
python -m script.learn_anomaly_sources [--dry-run] [--limit N] [--force-relearn] [--no-skip-processed]
python -m script.anomaly_summary [--date YYYY-MM-DD] [--limit N] [--timeout S] [--dry-run]

# ===== RAG 核心标的 =====
python -m script.rag.generate_rag --sector "板块名"        # 单板块生成
python -m script.rag.generate_rag_batch --sectors "板块1,板块2" --concurrency 3  # 并行批量
python -m script.rag.auto_match_sectors                     # 高分新闻自动关联板块
python -m script.service.auto_sync_sectors_rag             # 全量同步所有板块

# ===== 板块指数同步 =====
python -m script.sector.sync_sector_values
```

## 统一学习接口

`learn_source_config(url, name, headline, skip_article_crawler)` 同时完成列表发现和正文发现：

1. crawl4ai 获取渲染后的 HTML（列表页）
2. `discover_list_config` 分析列表配置（LLM/标题逆推/raw fetch）
3. 从列表页提取中间的文章 URL（避免置顶）
4. crawl4ai 获取文章页 HTML
5. `discover_content_config` 分析正文配置
6. 保存 `list_config` 和 `content_extract` 到 `source_crawl_configs`

**底层关键函数**（test_learn_flow.py 验证过）：

| 函数 | 用途 |
|------|------|
| `fetch_rendered_html` | crawl4ai 获取渲染后的 HTML |
| `clean_html` | 清洗列表页 HTML（移除无关标签） |
| `truncate_html_by_news_items` | 按新闻条目截断 HTML（限制大小） |
| `discover_list_config` | LLM 分析列表 DOM 配置 |
| `clean_article_html` | 清洗文章页 HTML |
| `discover_content_config` | LLM 分析正文配置 |

**调试命令**：
```bash
cd backend
python test_learn_flow.py --url "https://news.smm.cn/live"    # 完整流程
python test_learn_flow.py --url "https://news.smm.cn/live" --step 3  # 从 Step 3 开始
```

关键模块复用：
- `_fetch_html`：list_discovery._fetch_html（避免重复定义）
- `extract_article_links`：discovery.article_link_extractor（列表链接提取）
- `extract_news_list_from_rendered_html`：discovery.util.list_extractor（标题逆推）

## 目录结构

```
backend/
├── main.py                 # FastAPI 入口 + APScheduler 调度器
├── api/                    # REST API 路由
├── script/
│   ├── bootstrap.py        # 统一路径管理（APP_ROOT 自动推断）
│   ├── db/                 # 数据库操作（唯一合法入口）
│   │   ├── schema.sql      # 表结构定义（唯一定义源）
│   │   └── ...
│   ├── crawl/              # 采集管道
│   │   ├── list_crawler.py
│   │   ├── article_crawler.py
│   │   └── news_filter.py
│   ├── discovery/          # 配置发现（LLM 分析）
│   │   ├── list_discovery.py
│   │   └── content_discovery.py
│   ├── rag/                # RAG 报告生成
│   │   ├── generate_rag.py
│   │   └── parser.py
│   ├── llm/                # LLM 调用客户端
│   └── sector/             # 板块数据
news_board_app/             # Flutter 前端
```