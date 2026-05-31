# 新闻采集和分析

无人值守的一手新闻全量采集管道

## ⚠️ 代码规范（必须遵守）

### 代码生成
- **必须按照 `BEST_PRACTICE.md` 中的最佳实践生成代码**
- 涉及 Flutter/Dart 代码时，必须遵守 `docs/flutter-design.md` 和 `docs/flutter-ai-guide.md` 中的规范

### Python 依赖管理
- **新增 Python 模块必须在 `requirements.txt` 中登记**
- 禁止在代码中硬编码未在 `requirements.txt` 中声明的依赖
- 安装新依赖后，执行 `pip freeze > requirements.txt` 或手动添加

```bash
# 正确做法
# 1. 安装新模块
pip install some-package

# 2. 立即登记到 requirements.txt
pip freeze > requirements.txt
# 或手动添加
echo "some-package==x.x.x" >> requirements.txt
```

### 文件生成位置
- **所有 log 文件必须在 `logs/` 目录中生成**
- **所有 test 文件必须在各模块的 `test/` 目录或项目根目录 `test/` 目录中生成**
- 禁止在业务代码目录中直接创建 log 或 test 文件

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

### 1. 安装依赖
```bash
# Windows
init.bat

# Linux/Mac
bash init.sh
```

这将：
- 安装所有 Python 依赖（crawl4ai, fastapi, pypinyin 等）
- 安装 Flutter 依赖（如果 Flutter 已安装）
- 执行 init_db.py 初始化数据库

或手动安装：
```bash
pip install -r requirements.txt
python init_db.py
```

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

## Step 5: 板块指数查询

### 目标
- `importance.publish_sector_values` - 首次填充（关联板块为空时）
- `importance.current_sector_values` - 更新（高分 + 最近7天）

### 数据格式
```
板块名:指数值|板块名:指数值
示例：稀土永磁:1200.5|芯片概念:850.3|军工:2300.8
```

### 更新条件
| 字段 | 条件 |
|------|------|
| publish_sector_values | `related_sectors` 不为空 AND 字段为空 |
| current_sector_values | `related_sectors` 不为空 AND `importance_score` >= 7 AND `created_at` 在最近 7 天内 |

**注意**：当一条记录同时满足两个条件时，一次填充两个字段

### 方案（一次查询 + 批量匹配）
1. 调用同花顺接口，问句 `二级行业或二级概念板块`，一次查询所有板块当前指数值（loop=5 获取全量 480 条）
2. 构建 `{板块code: 指数值}` 和 `{板块名: 指数值}` 字典
3. 遍历 importance 记录，根据 `related_sectors` 匹配，批量填充/更新

### 实现脚本
```bash
python script/sector/sync_sector_values.py
```

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