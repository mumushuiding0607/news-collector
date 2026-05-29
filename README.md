# 新闻采集和分析

无人值守的一手新闻全量采集管道

## 目录结构

```
新闻采集/
├── db/
│   └── primary.db      # SQLite 数据库（自动生成）
├── init_db.py          # 数据库初始化入口
├── script/
│   ├── common/         # 公共模块
│   │   ├── __init__.py # 初始化工具（init_all, sync_sectors 等）
│   │   └── db/
│   │       ├── schema.sql   # 数据库表结构（唯一定义源）
│   │       ├── connection.py # 数据库连接
│   │       ├── primary_source.py # 一手新闻表
│   │       ├── importance.py   # 评分表
│   │       ├── sectors.py     # 板块归一化
│   │       └── ...
│   ├── crawl/          # 采集脚本
│   │   ├── crawler.py  # 采集入口
│   │   ├── article_crawler.py
│   │   └── ...
│   └── ...
├── config/
│   └── sources.json    # 数据源配置
├── logs/               # 运行日志
└── prompt/
    └── 事件评估.md      # 评分提示词模板
```

## 快速开始

### 1. 初始化数据库（首次部署）
```bash
python init_db.py
```

这将：
- 执行 schema.sql 创建所有表（primary_sources, importance, sectors, sector_indices 等）
- 验证 FTS5 虚拟表是否正常
- 从同花顺同步 480 条板块数据

### 2. 运行采集
```bash
python -m script.crawl.crawler
```

## 数据库初始化

### init_db.py - 初始化入口

```bash
# 一键初始化（创建表 + 同步sectors）
python init_db.py

# 仅检查状态
python init_db.py --check-only

# 强制重新同步sectors
python init_db.py --force-sync

# 强制修复FTS5
python init_db.py --force-repair
```

### common/__init__.py - 初始化工具

```python
from common import init_all, check_tables, sync_sectors

# 一键初始化
init_all()

# 检查表结构
check_tables()

# 检查sectors数据
count = sectors_count()

# 强制同步sectors
sync_sectors(loop=5)
```

### schema.sql - 表结构唯一定义源

**重要**：所有表结构定义在 `script/common/db/schema.sql` 中，是唯一的表结构定义源。

修改表结构只需编辑 `schema.sql`，然后运行 `init_db.py` 即可同步。

包含：
- primary_sources（一手新闻表）
- importance（评分表）
- sectors（板块表）
- sector_indices（板块指数表）
- sectors_fts（FTS5全文索引）
- 触发器（sectors_ai, sectors_ad, sectors_au）

## 工作流程

### Step 1: 采集 (crawler.py)
```bash
python -m script.crawl.crawler
```
- 从列表页提取文章URL+标题
- 逐篇抓取正文 → 日期过滤 → 入库
- 只采集当天的新闻

### Step 2: LLM过滤 (news_filter.py)
- 读取 is_useful=0 的新闻
- 调用LLM判断是否会引起交易市场波动
- 标记 is_useful=1 则后续采集正文

### Step 3: 采集正文 (article_crawler.py)
- 读取 is_useful=1 且 status='new' 的记录
- 抓取文章正文 → 提取发布时间 → 入库

### Step 4: 评分 (read_news.py)
```bash
python script/read_news.py
```
- 调用LLM生成摘要、关联板块、评分
- 存入 importance 表

## 数据库表

### primary_sources - 一手新闻表
- id, source_name, title, url, subtitle, publish_time, content
- status ('new'/'read'), fetched_at

### importance - 评分表
- id, news_id, source_name, title, url, publish_time
- summary, related_sectors (归一化后的板块名，用|分隔)
- importance_score (1-10)
- reason, direction, intensity, expected_change, duration
- expectation_level, market_mode
- created_at (批次时间)

### sectors - 板块表
- id, code, name, name_pinyin_initial, name_pinyin_full, keywords
- 用于归一化LLM输出的板块名

### sector_indices - 板块指数记录表
- id, importance_id, sector_code, sector_name
- change_rate, turnover, volume, amount, dde_net_amount
- query_time

## 板块归一化

LLM输出的板块名通过本地sectors表归一化，不消耗额外token：

```python
from common import normalize

# LLM返回"稀土|芯片|AI"
results = normalize("稀土|芯片|AI")
# -> [
#     {"code": "885343", "name": "稀土永磁", "raw": "稀土", "normalized": True},
#     {"code": "885756", "name": "芯片概念", "raw": "芯片", "normalized": True},
#     {"code": "885887", "name": "数据中心(AIDC)", "raw": "AI", "normalized": True}
#   ]
```

匹配策略（按优先级）：
1. 精确匹配（名称完全一致）
2. 拼音首字母匹配（仅精确匹配）
3. FTS5全文搜索
4. keywords关键词匹配

## 评分框架（事件评估.md）

基于四维预期定性框架：
- 影响强度：1～5级
- 预期价格波幅：±%
- 持续时间：超短期/短期/中期/长期/永久
- 四维定性：宏大叙事/消息、全市场/单一资金、模糊/清晰、基本面深度

综合评分 = 影响强度×0.7 + 波幅得分×0.15 + 持续时间×0.15