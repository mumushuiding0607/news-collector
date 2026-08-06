import api from "../client";

export const getNewsList = (params: Record<string, unknown>) =>
  api.get("/api/news/list", { params });

export const getPrimarySourcesList = (params: Record<string, unknown>) =>
  api.get("/api/news/primary_sources", { params });

export const getLatestNews = (params: Record<string, unknown>) =>
  api.get("/api/news/latest", { params });

export const getHotNews = (params: Record<string, unknown>) =>
  api.get("/api/news/hot", { params });

// AI 新闻
export const getAiLatestNews = () =>
  api.get("/api/news/ai/latest");

export const getAiHistoryNews = () =>
  api.get("/api/news/ai/history");

export const getAiAllNews = () =>
  api.get("/api/news/ai/all");

export const getAiNewsList = (params: Record<string, unknown>) =>
  api.get("/api/news/ai/list", { params });

export const getNewsDetail = (newsId: number) =>
  api.get(`/api/news/detail/${newsId}`);

export const markUseful = (id: number, useful: boolean) =>
  api.post("/api/news/mark_useful", { id, useful });

export const runPipelineStep = (step: number) =>
  api.post("/api/news/pipeline/step", null, { params: { step } });

export const runPipelineFull = () =>
  api.post("/api/news/pipeline/run");

// 数据源学习/抓取（与 news 流水线相关）
export const learnSource = (params: { url: string; name?: string; headline?: string; skip_article?: boolean; force_relearn?: boolean; news_type?: string }) =>
  api.get("/api/news/learn", { params });

export const learnSourceAsync = (params: { url: string; name?: string; headline?: string; skip_article?: boolean; news_type?: string }) =>
  api.get("/api/news/learn_async", { params });

export const fetchSourceNews = (params: { url: string; limit?: number; news_type?: string }) =>
  api.get("/api/news/fetch", { params });

export const fetchSourceNewsAsync = (params: { url: string; limit?: number; news_type?: string }) =>
  api.get("/api/news/fetch_async", { params });

export const fetchArticleContent = (url: string, sourceName?: string) =>
  api.get("/api/news/article", { params: { url, source_name: sourceName || "" } });

export const previewUrlContent = (url: string) =>
  api.get("/api/news/url-preview", { params: { url } });

// 异动消息流水线（消息流和数据源流都通过 news 入口触发）
export const runAnomalyNewsPipelineStep = (step: number) =>
  api.post("/api/news/anomaly-pipeline/news/step", null, { params: { step } });

export const runAnomalyNewsPipeline = () =>
  api.post("/api/news/anomaly-pipeline/news/run");

export const runAnomalySourcePipelineStep = (step: number) =>
  api.post("/api/news/anomaly-pipeline/source/step", null, { params: { step } });
