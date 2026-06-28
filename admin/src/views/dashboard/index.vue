<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getUsers } from "../../api";

const stats = ref([
  { label: "用户总数", value: 0, color: "var(--accent)" },
  { label: "Pro 订阅", value: 0, color: "var(--success)" },
  { label: "Premium 订阅", value: 0, color: "var(--gold)" },
  { label: "待处理反馈", value: 0, color: "var(--warning)" },
]);

const recentUsers = ref<Record<string, unknown>[]>([]);

onMounted(async () => {
  try {
    const data = await getUsers({ limit: 5 }) as { users?: Record<string, unknown>[] };
    recentUsers.value = data.users || [];
  } catch (e) {
    console.error(e);
  }
});
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">控制台</h2>
    <el-row :gutter="20">
      <el-col v-for="(s, i) in stats" :key="i" :span="6">
        <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; text-align: center; box-shadow: var(--shadow-card)">
          <div style="color: var(--text-muted); font-size: 14px">{{ s.label }}</div>
          <div :style="{ color: s.color, fontSize: '32px', fontWeight: 'bold', marginTop: '8px' }">{{ s.value }}</div>
        </div>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
      <template #header>
        <span style="color: var(--gold)">最新用户</span>
      </template>
      <el-table :data="recentUsers" style="background: transparent; color: var(--text)" stripe>
        <el-table-column prop="phone" label="手机号" />
        <el-table-column prop="subscription_level" label="订阅等级" />
        <el-table-column prop="created_at" label="注册时间" />
      </el-table>
    </el-card>
  </div>
</template>