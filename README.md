# 新闻采集和分析

无人值守的一手新闻全量采集管道1.

## 目录结构

```
新闻采集和分析/
├── db/
│   ├── schema.sql      # 数据库表结构
│   └── primary.db      # SQLite 数据库（自动生成）
├── config/
│   └── sources.json    # 一手数据源清单
├── logs/               # 运行日志
└── README.md
```

## 数据源

| 来源 | 类型 | 状态 |
|------|------|------|
| 证监会-要闻 | static | ✅ |
| 上交所-上市公司公告 | static | ✅ |
| 深交所-上市公司公告 | static | ✅ |
| 北交所-上市公司公告 | static | ✅ |
| 人民银行-公开市场操作 | static | ✅ |
| 国家统计局-数据发布 | static | ✅ |
| 巨潮资讯-最新公告 | static | ✅ |
| 深交所互动易-最新问答 | dynamic | ⚠️ 需配置 browser_profile |

## 数据库表

### primary_sources（一手新闻主表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| source_name | TEXT | 来源名称 |
| title | TEXT | 标题 |
| url | TEXT | 链接（唯一） |
| publish_time | TEXT | 发布时间 |
| content | TEXT | 公告全文 |
| status | TEXT | new/fetched/pushed/error |
| fetched_at | TEXT | 采集时间 |

### collect_log（采集日志表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| source_name | TEXT | 来源名称 |
| url | TEXT | 链接 |
| status | TEXT | 状态 |
| note | TEXT | 备注 |
| created_at | TEXT | 创建时间 |

## 定时任务

- **采集频率**：交易日每15分钟
- **Cron 表达式**：`*/15 9-15 * * 1-5`（Asia/Shanghai）
