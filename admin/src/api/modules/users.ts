import api from "../client";

export const getUsers = (params: Record<string, unknown>) =>
  api.get("/api/admin/users", { params });

export const getUserDetail = (id: number) =>
  api.get(`/api/admin/users/${id}`);

export const updateUserLevel = (id: number, level: string, days: number) =>
  api.post(`/api/admin/users/${id}/level`, { level, days });
