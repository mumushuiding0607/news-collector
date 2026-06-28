import api from "../client";

export const getAnomalyNewsList = (params: { source_name?: string; processed?: number; page?: number; limit?: number }) =>
  api.get("/api/admin/anomaly-news", { params });

export const deleteAnomalyNews = (id: number) =>
  api.delete(`/api/admin/anomaly-news/${id}`);

export const markAnomalyProcessed = (id: number) =>
  api.post(`/api/admin/anomaly-news/${id}/processed`);

export const markAllAnomalyProcessed = () =>
  api.post("/api/admin/anomaly-news/mark-all-processed");
