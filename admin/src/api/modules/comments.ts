import api from "../client";

export const getComments = (params: { news_id?: number; page?: number; limit?: number }) =>
  api.get("/api/admin/comments", { params });

export const getFeedbackSummary = (params: { news_id?: number; page?: number; limit?: number }) =>
  api.get("/api/admin/feedback-summary", { params });
