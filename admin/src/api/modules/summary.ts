import api from "../client";

export const getSummaries = (params: { type?: string; page?: number; limit?: number }) =>
  api.get("/api/admin/summaries", { params });

export const getSummaryByDate = (date: string, type?: string) =>
  api.get(`/api/admin/summary/${date}`, { params: type ? { type } : {} });
