import api from "../client";

export const getLogDates = () => api.get("/api/logs/dates");

export const getLogFiles = (date?: string) =>
  api.get("/api/logs/files", { params: date ? { date } : {} });

export const getLogContent = (path: string, offset?: number, limit?: number) =>
  api.get("/api/logs/content", { params: { path, offset: offset || 0, limit: limit || 500 } });
