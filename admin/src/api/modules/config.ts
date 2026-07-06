import api from "../client";

export const getAppConfig = () => api.get("/api/config/app");

export const updateAppConfig = (data: Record<string, unknown>) =>
  api.post("/api/config/app", data);

export const getEnvConfig = () => api.get("/api/config/env");

export const updateEnvConfig = (data: Record<string, unknown>) =>
  api.post("/api/config/env", data);

export const getSubscriptionTiers = () =>
  api.get("/api/config/subscription_tiers");

export const updateSubscriptionTiers = (tiers: Record<string, unknown>[]) =>
  api.post("/api/config/subscription_tiers", tiers);

export const getSourcesConfig = () => api.get("/api/config/sources");

export const updateSourcesConfig = (data: Record<string, unknown>) =>
  api.post("/api/config/sources", data);
