<script setup lang="ts">
import { ref } from "vue";
import { ElMessageBox } from "element-plus";
import NewsList from "./NewsList.vue";
import NewsSummary from "./NewsSummary.vue";
import { pipelineSteps } from "./pipelineConfig";
import { runPipelineStep, runPipelineFull } from "../../api";
import NewsDetail from "../../components/NewsDetail.vue";
import LogViewer from "../../components/LogViewer.vue";
import type { TabType } from "./types";

const activeTab = ref<TabType>("importance");

const detailVisible = ref(false);
const detailNewsId = ref<number | null>(null);
const detailSource = ref<"news" | "primary">("news");

const logVisible = ref(false);
const logTitle = ref("");
const logFile = ref("");

async function handlePipelineStep(step: number, desc: string) {
  try {
    await ElMessageBox.confirm(`确认执行「${desc}」？`, "确认执行", { type: "info" });
  } catch {
    return;
  }
  const cfg = pipelineSteps.find((s) => s.step === step);
  logTitle.value = `Pipeline - ${desc}`;
  logFile.value = `${cfg?.logFile}.log`;
  logVisible.value = true;
  try {
    if (step === 0) {
      await runPipelineFull();
    } else {
      await runPipelineStep(step);
    }
  } catch {
    // interceptor shows popup
  }
}

function openDetail(id: number) {
  detailNewsId.value = id;
  detailSource.value = activeTab.value === "primary" ? "primary" : "news";
  detailVisible.value = true;
}

function onTabChange(tab: string | number) {
  activeTab.value = tab as TabType;
}
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">新闻管理</h2>

    <el-tabs :model-value="activeTab" @tab-change="onTabChange" style="margin-bottom: 16px">
      <el-tab-pane label="重要性分析" name="importance" />
      <el-tab-pane label="原始数据" name="primary" />
      <el-tab-pane label="热点新闻" name="summary" />
    </el-tabs>

    <NewsList
      v-if="activeTab !== 'summary'"
      :tab="activeTab as 'importance' | 'primary'"
      :pipeline-steps="activeTab === 'importance' ? pipelineSteps : []"
      @open-pipeline="handlePipelineStep"
      @open-detail="openDetail"
    />
    <NewsSummary v-else />

    <NewsDetail v-model:visible="detailVisible" :news-id="detailNewsId" :source="detailSource" />

    <LogViewer v-model:visible="logVisible" :log-file="logFile" :title="logTitle" />
  </div>
</template>
