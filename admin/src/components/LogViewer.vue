<script setup lang="ts">
import { ref, watch, onUnmounted } from "vue";
import { getLogDates, getLogFiles, getLogContent } from "../api";
import { useMobile } from "../composables/useMobile";
import LogSidebar from "./log/LogSidebar.vue";
import LogContent from "./log/LogContent.vue";

const { isMobile } = useMobile();

const props = defineProps<{
  visible: boolean;
  logFile?: string;
  title?: string;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

const dates = ref<string[]>([]);
const files = ref<Record<string, unknown>[]>([]);
const selectedDate = ref("");
const selectedFile = ref<Record<string, unknown> | null>(null);
const logLines = ref<string[]>([]);
const loading = ref(false);
const refreshTimer = ref<ReturnType<typeof setInterval> | null>(null);

async function fetchDates() {
  try {
    const res = (await getLogDates()) as { dates?: string[] };
    dates.value = res.dates || [];
    if (dates.value.length > 0 && !selectedDate.value) {
      selectedDate.value = dates.value[0];
    }
  } catch (e) {
    console.error(e);
  }
}

async function fetchFiles(date: string) {
  loading.value = true;
  logLines.value = [];
  selectedFile.value = null;
  try {
    const res = (await getLogFiles(date)) as { files?: Record<string, unknown>[] };
    files.value = res.files || [];
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function fetchLogContent(path: string) {
  if (!path) return;
  try {
    const res = (await getLogContent(path, 0, 100)) as { lines?: string[] };
    // Backend already reverses (newest first), no need to reverse again
    logLines.value = res.lines || [];
  } catch (e) {
    console.error(e);
  }
}

function startAutoRefresh(filePath: string) {
  stopAutoRefresh();
  refreshTimer.value = setInterval(() => {
    if (props.visible) {
      fetchLogContent(filePath);
    }
  }, 10000);
}

function stopAutoRefresh() {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
}

function selectFile(file: Record<string, unknown>) {
  selectedFile.value = file;
  fetchLogContent(file.path as string);
  startAutoRefresh(file.path as string);
}

function handleClose() {
  stopAutoRefresh();
  emit("update:visible", false);
}

function handleRefresh() {
  if (selectedFile.value) {
    fetchLogContent(selectedFile.value.path as string);
  }
}

async function initLogViewer() {
  selectedDate.value = "";
  selectedFile.value = null;
  logLines.value = [];
  files.value = [];
  dates.value = [];
  await fetchDates();

  if (props.logFile && selectedDate.value) {
    await fetchFiles(selectedDate.value);
    const targetFile = files.value.find((f) => (f.name as string)?.includes(props.logFile as string));
    if (targetFile) selectFile(targetFile);
  } else if (files.value.length > 0) {
    const targetFile = files.value.find((f) => (f.name as string)?.includes("list_discovery")) || files.value[0];
    if (targetFile) selectFile(targetFile);
  }
}

watch(selectedDate, async (newDate) => {
  if (newDate) {
    await fetchFiles(newDate);
    if (!props.logFile && files.value.length > 0) {
      selectFile(files.value[0]);
    }
  }
});

watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    initLogViewer();
  } else {
    stopAutoRefresh();
  }
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    :title="title || '日志查看'"
    :fullscreen="isMobile"
    :close-on-click-modal="false"
    :body-style="isMobile ? 'padding: 12px; height: calc(100vh - 110px)' : 'padding: 16px; min-height: 400px'"
  >
    <div v-if="!isMobile" style="display: flex; gap: 20px; min-height: 400px; height: 60vh">
      <LogSidebar
        :dates="dates"
        :files="files"
        v-model:selectedDate="selectedDate"
        :selected-file="selectedFile"
        :loading="loading"
        :is-mobile="false"
        @select-file="selectFile"
      />
      <LogContent :lines="logLines" :loading="loading" :is-mobile="false" @refresh="handleRefresh" />
    </div>

    <div v-else style="display: flex; flex-direction: column; gap: 12px; height: calc(100vh - 110px)">
      <LogSidebar
        :dates="dates"
        :files="files"
        v-model:selectedDate="selectedDate"
        :selected-file="selectedFile"
        :loading="loading"
        :is-mobile="true"
        @select-file="selectFile"
      />
      <LogContent :lines="logLines" :loading="loading" :is-mobile="true" @refresh="handleRefresh" />
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>
