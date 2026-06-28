import api from "../client";

export const getSubscriptionPlans = () => api.get("/api/subscription/plans");

export const getSubscriptionCurrent = () => api.get("/api/subscription/current");

export const createSubscriptionOrder = (level: string) =>
  api.post("/api/subscription/create_order", { level });

export const getOrderStatus = (orderNo: string) =>
  api.get(`/api/subscription/order/${orderNo}`);

export const confirmPayment = (orderNo: string, payAccountNote: string) =>
  api.post("/api/subscription/confirm_payment", { order_no: orderNo, pay_account_note: payAccountNote });

// Admin 端订阅审批
export const getPendingSubscriptions = () =>
  api.get("/api/admin/subscriptions/pending");

export const confirmSubscription = (userId: number) =>
  api.post(`/api/admin/subscriptions/${userId}/confirm`);

export const updateSubscriptionLevel = (userId: number, level: string, days: number) =>
  api.post(`/api/admin/subscriptions/${userId}/level`, { level, days });

export const rejectSubscription = (userId: number, reason?: string) =>
  api.post(`/api/admin/subscriptions/${userId}/reject`, { reason: reason || "" });
