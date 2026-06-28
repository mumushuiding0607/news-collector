<script setup lang="ts">
import { ref } from "vue";
import SourcesConfigList from "./SourcesConfigList.vue";
import LearnDialog from "./dialogs/LearnDialog.vue";
import FetchDialog from "./dialogs/FetchDialog.vue";
import FetchResultDialog from "./dialogs/FetchResultDialog.vue";
import ArticleDialog from "./dialogs/ArticleDialog.vue";
import AnomalyDialog from "./dialogs/AnomalyDialog.vue";
import LogViewer from "../../components/LogViewer.vue";

const activeTab = ref("configs");

// 日志查看
const logViewerVisible = ref(false);
const logViewerTitle = ref("");
const logViewerFile = ref("");

// 学习弹窗
const learnVisible = ref(false);
const learnRow = ref<Record<string, unknown> | null>(null);

// 抓取输入弹窗
const fetchVisible = ref(false);
const fetchInitialUrl = ref("");

// 抓取结果弹窗
const resultVisible = ref(false);
const resultData = ref<Record<string, unknown>[]>([]);
const resultSourceName = ref("");

// 文章正文弹窗
const articleVisible = ref(false);
const articleRow = ref<Record<string, unknown> | null>(null);

// 异动弹窗
const anomalyVisible = ref(false);
const anomalySourceName = ref("");

function openLearn(row?: Record<string, unknown>) {
  learnRow.value = row || null;
  learnVisible.value = true;
}

function openFetch(row?: Record<string, unknown>) {
  fetchInitialUrl.value = row ? ((row.url_norm as string) || "") : "";
  fetchVisible.value = true;
}

function onFetched(payload: { url: string; sourceName: string; news: Record<string, unknown>[] }) {
  resultSourceName.value = payload.sourceName;
  resultData.value = payload.news;
  resultVisible.value = true;
  logViewerVisible.value = false;
}

function openArticle(row: Record<string, unknown>) {
  articleRow.value = row;
  articleVisible.value = true;
}

function openAnomaly(row: Record<string, unknown>) {
  anomalySourceName.value = (row.name as string) || "";
  anomalyVisible.value = true;
}

function onTaskStarted(payload: { sourceName: string; logFile: string }) {
  logViewerTitle.value = `抓取日志 - ${payload.sourceName}`;
  logViewerFile.value = payload.logFile;
  logViewerVisible.value = true;
}

function onLearnStarted(payload: { sourceName: string; logFile: string }) {
  logViewerTitle.value = `学习日志 - ${payload.sourceName}`;
  logViewerFile.value = payload.logFile;
  logViewerVisible.value = true;
}
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">数据源配置管理</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="数据源配置" name="configs">
        <SourcesConfigList
          @learn="openLearn"
          @fetch="openFetch"
          @anomaly="openAnomaly"
        />
      </el-tab-pane>
    </el-tabs>

    <LearnDialog
      v-model:visible="learnVisible"
      :initial-row="learnRow"
      @started="onLearnStarted"
    />

    <FetchDialog
      v-model:visible="fetchVisible"
      :initial-url="fetchInitialUrl"
      @fetched="onFetched"
    />

    <FetchResultDialog
      v-model:visible="resultVisible"
      :data="resultData"
      :loading="false"
      @fetch-article="openArticle"
    />

    <ArticleDialog
      v-model:visible="articleVisible"
      :row="articleRow"
      :source-name="resultSourceName"
    />

    <AnomalyDialog
      v-model:visible="anomalyVisible"
      :source-name="anomalySourceName"
    />

    <LogViewer
      v-model:visible="logViewerVisible"
      :log-file="logViewerFile"
      :title="logViewerTitle"
    />
  </div>
</template>
