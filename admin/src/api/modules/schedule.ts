import api from "../client";

export const getScheduleTasks = () => api.get("/api/schedule/tasks");

export const getScheduleTask = (id: string) => api.get(`/api/schedule/tasks/${id}`);

export const createScheduleTask = (data: Record<string, unknown>) =>
  api.post("/api/schedule/tasks", data);

export const updateScheduleTask = (id: string, data: Record<string, unknown>) =>
  api.put(`/api/schedule/tasks/${id}`, data);

export const deleteScheduleTask = (id: string) =>
  api.delete(`/api/schedule/tasks/${id}`);

export const triggerScheduleTask = (id: string) =>
  api.post(`/api/schedule/tasks/${id}/trigger`);
