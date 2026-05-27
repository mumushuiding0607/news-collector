---
name: news-collect
description: "新闻采集 TaskFlow 工作流。"
metadata: { "openclaw": { "emoji": "📰" } }
---

# 新闻采集 TaskFlow

## 工作流步骤

```yaml
name: news-collect
steps:
  - id: crawl
    command: python 新闻采集/script/crawl_news.py

  - id: report
    command: >-
      openclaw.invoke --tool llm-task --action json --args-json
      '{"prompt":"读取 logs/crawl_YYYYMMDD.log，返回采集结果摘要：信源数、新增条数、跳过条数、异常信源。","thinking":"low","schema":{"type":"object","properties":{"total_sources","new_count","skipped_count","errors":[]},"required":["total_sources","new_count"]}}'
```

## stateJson

```json
{
  "crawled_at": "",
  "total_sources": 0,
  "new_count": 0,
  "skipped_count": 0,
  "errors": []
}
```

## 注意事项

- 日志路径：`新闻采集/logs/crawl_YYYYMMDD.log`
- 脚本会自动写入 `primary.db`（URL 去重）
- Windows 编码：日志中避免 Unicode 特殊字符