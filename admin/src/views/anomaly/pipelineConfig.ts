// 异动消息 pipeline 步骤定义
export const newsPipelineSteps = [
  { step: 1, name: "fetch_anomalies",   desc: "采集异动消息入库", logFile: "anomaly_fetcher" },
  { step: 2, name: "crawl_contents",   desc: "采集文章正文",     logFile: "anomaly_fetcher" },
  { step: 3, name: "confirm_sources",  desc: "确认数据源",       logFile: "confirm_anomaly" },
  { step: 4, name: "generate_summary", desc: "生成异动简报",     logFile: "anomaly_summary" },
];

// 独立数据源步骤
export const sourcePipelineSteps = [
  { step: 1, name: "confirm_sources", desc: "确认数据源", logFile: "confirm_anomaly" },
];
