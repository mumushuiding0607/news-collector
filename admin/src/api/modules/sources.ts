import api from "../client";

// 数据源配置（source_crawl_configs）
export const createCrawlConfig = (data: { name: string; url_norm: string }, news_type: string = "stock") =>
  api.post("/api/admin/crawl-configs", data, { params: { news_type } });

export const getCrawlConfigs = (params: { checked?: number; page?: number; limit?: number; news_type?: string }) =>
  api.get("/api/admin/crawl-configs", { params });

export const confirmCrawlConfig = (configId: number, news_type: string = "stock") =>
  api.post(`/api/admin/crawl-configs/${configId}/confirm`, {}, { params: { news_type } });

export const unconfirmCrawlConfig = (configId: number, news_type: string = "stock") =>
  api.post(`/api/admin/crawl-configs/${configId}/unconfirm`, {}, { params: { news_type } });

export const deleteCrawlConfig = (configId: number, news_type: string = "stock") =>
  api.delete(`/api/admin/crawl-configs/${configId}`, { params: { news_type } });

export const updateCrawlConfig = (configId: number, data: { name?: string; url_norm?: string; list_config?: string; content_extract?: string; crawl_order?: number; is_flash?: number }, news_type: string = "stock") =>
  api.put(`/api/admin/crawl-configs/${configId}`, data, { params: { news_type } });

export const getCrawlConfigSourceNames = (news_type: string = "stock") =>
  api.get("/api/admin/crawl-configs/source_names", { params: { news_type } });

// 原始数据（primary_sources）
export const deletePrimarySourcesByDate = (date: string) =>
  api.delete("/api/admin/primary_sources/by_date", { params: { date } });

export const getPrimarySourceDetail = (id: number) =>
  api.get(`/api/admin/primary_sources/${id}`);

// 异动消息
export const getAnomalyNews = (params: { sourceName?: string; title?: string; processed?: number; page?: number; limit?: number }) =>
  api.get("/api/admin/anomaly-news", { params });
