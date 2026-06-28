// 订阅套餐基础价格表（同步展示用，与后端 tiers 配置无关）
export const SUBSCRIPTION_PLANS: Record<string, { name: string; price: number; duration_days: number }> = {
  pro: { name: "专业版", price: 99, duration_days: 30 },
  premium: { name: "高级版", price: 299, duration_days: 90 },
};

export function getPlanPrice(level: string): number {
  return SUBSCRIPTION_PLANS[level]?.price ?? 0;
}
