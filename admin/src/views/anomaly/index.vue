<script setup lang="ts">
import { ref } from "vue";
import AnomalyList from "./AnomalyList.vue";
import AnomalySummary from "./AnomalySummary.vue";
import LogViewer from "../../components/LogViewer.vue";

const activeTab = ref("news");
const logVisible = ref(false);
const logTitle = ref("异动消息处理日志");
const logFile = ref("anomaly_fetcher.log");

function openLog(title: string, file: string) {
  logTitle.value = title;
  logFile.value = file;
  logVisible.value = true;
}
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">异动消息</h2>

    <el-tabs v-model="activeTab" style="margin-bottom: 16px">
      <el-tab-pane label="异动消息" name="news" />
      <el-tab-pane label="异动简报" name="summary" />
    </el-tabs>

    <AnomalyList v-if="activeTab === 'news'" @open-log="openLog" />
    <AnomalySummary v-else @open-log="openLog" />

    <LogViewer v-model:visible="logVisible" :log-file="logFile" :title="logTitle" />
  </div>
</template>
