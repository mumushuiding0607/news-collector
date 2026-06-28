// 新闻采集 pipeline 步骤定义（与后端 backend/main.py 中注册的 step 对应）
export const pipelineSteps = [
  { step: 1, name: "list_crawler", desc: "采集新闻列表", logFile: "list_crawler" },
  { step: 2, name: "news_filter", desc: "LLM过滤", logFile: "news_filter" },
  { step: 3, name: "article_crawler", desc: "采集文章正文", logFile: "article_crawler" },
  { step: 4, name: "scorer", desc: "LLM评分", logFile: "scorer" },
  { step: 5, name: "findStocks", desc: "核心标的发现", logFile: "find_stocks" },
  { step: 6, name: "sync_sector_values", desc: "同步板块指数", logFile: "sync_sector_values" },
  { step: 7, name: "update_cache", desc: "更新新闻缓存", logFile: "update_cache" },
];
