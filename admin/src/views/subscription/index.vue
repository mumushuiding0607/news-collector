<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import PlansPanel from "./PlansPanel.vue";
import PendingPanel from "./PendingPanel.vue";

const route = useRoute();
const router = useRouter();

// 根据 URL 决定激活的 tab（pending 是子路由）
const activeTab = ref(route.name === "SubscriptionsPending" ? "pending" : "plans");

function onTabChange(tab: string) {
  if (tab === "pending") {
    router.push("/subscriptions/pending");
  } else {
    router.push("/subscriptions");
  }
}
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">订阅管理</h2>

    <el-tabs :model-value="activeTab" type="border-card" style="background: transparent" @tab-change="onTabChange">
      <el-tab-pane label="订阅套餐" name="plans">
        <PlansPanel />
      </el-tab-pane>
      <el-tab-pane label="待确认用户" name="pending">
        <PendingPanel />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
