# 新闻采集和分析

无人值守的一手新闻全量采集管道

## 目录结构

```
新闻采集/
├── db/
│   ├── schema.sql      # 数据库表结构
│   ├── primary.db      # SQLite 数据库（自动生成）
│   └── __init__.py     # 数据库模块
├── config/
│   └── sources.json    # 数据源配置
├── logs/               # 运行日志
├── prompt/
│   └── 事件评估.md      # 评分提示词模板
├── script/
│   ├── crawl_news.py    # 新闻采集（Step1）
│   ├── read_news.py     # 新闻评分（Step2）
│   ├── sector_index.py  # 板块指数查询（Step3）
│   ├── report.py        # 报告生成（Step4）
│   ├── content_filter.py # 内容过滤
│   ├── util.py          # 工具函数
│   ├── llm_client.py    # LLM调用封装
│   ├── iwencai.py       # 同花顺数据查询
│   ├── hexin-v.bundle.cjs # Token生成器
│   ├── wencai_headers.json # 缓存
│   └── db/
│       ├── __init__.py
│       ├── connection.py  # 数据库连接
│       ├── primary_source.py # 一手新闻表
│       ├── importance.py   # 评分表
│       └── sectors.py     # 板块归一化
└── README.md
```

## 工作流程

### Step 1: 采集 (crawl_news.py)
```bash
python script/crawl_news.py
```
- 从列表页提取文章URL+标题（不写库）
- 逐篇抓取正文 → 提取真实发布时间 → 日期过滤 → 完整正文入库
- 只采集当天的新闻

### Step 2: 评分 (read_news.py)
```bash
python script/read_news.py [--limit N] [--dry-run]
```
- 读取 status='new' 的新闻
- 调用LLM判断是否会引起交易市场波动
- 若能：生成摘要、关联板块（归一化）、评分，存入 importance 表
- 标记新闻为已读
- 同一时间段评分的新闻算同一批次

### Step 3: 关联板块指数 (sector_index.py)
```bash
python script/sector_index.py query <板块名>
python script/sector_index.py batch <板块1,板块2>
```
- 批量查询板块当前指数和涨跌幅
- 归一化LLM输出的板块名（零token）
- 支持查询特定新闻发布瞬间的板块指数

### Step 4: 输出报告 (report.py)
```bash
python script/report.py [--top N] [--json] [--save FILE]
```
- 查询最新批次的高评分新闻
- 批量查询关联板块涨跌幅
- 计算新闻发布至今的涨跌幅
- 生成格式化报告

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
from db.sectors import normalize

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