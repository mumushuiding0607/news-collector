<script setup lang="ts">
import { ref, watch } from "vue";
import { previewUrlContent } from "../api";
import { Loading } from "@element-plus/icons-vue";

const props = defineProps<{
  visible: boolean;
  url: string;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

const loading = ref(false);
const content = ref("");
const contentLength = ref(0);
const method = ref("");

async function fetchContent() {
  if (!props.url) return;
  loading.value = true;
  try {
    const res = await previewUrlContent(props.url) as { ok?: boolean; content?: string; content_length?: number; method?: string };
    if (res?.ok) {
      content.value = res.content || "";
      contentLength.value = res.content_length || 0;
      method.value = res.method || "";
    } else {
      content.value = "获取内容失败";
    }
  } catch (e) {
    console.error(e);
    content.value = "加载失败";
  } finally {
    loading.value = false;
  }
}

function close() {
  emit("update:visible", false);
}

function openInBrowser() {
  window.open(props.url, "_blank");
}

watch(() => props.visible, (val) => {
  if (val && props.url) {
    content.value = "";
    fetchContent();
  }
});
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="close"
    title="网页预览"
    :fullscreen="true"
    width="95%"
    style="max-width: 900px"
    destroy-on-close
  >
    <div v-if="loading" style="text-align: center; padding: 60px 0">
      <el-icon class="is-loading" style="font-size: 32px; color: var(--primary)"><Loading /></el-icon>
      <div style="margin-top: 12px; color: var(--text-muted)">正在抓取页面内容...</div>
    </div>

    <div v-else-if="content" style="display: flex; flex-direction: column; height: 100%">
      <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px">
        <div style="font-size: 12px; color: var(--text-muted)">
          {{ contentLength }} 字 · 抓取方式: {{ method }}
        </div>
        <el-button type="primary" link @click="openInBrowser">
          在浏览器中打开
        </el-button>
      </div>
      <div style="flex: 1; overflow-y: auto; color: var(--text); line-height: 1.9; font-size: 15px; white-space: pre-wrap; background: var(--bg); border-radius: 8px; padding: 20px; border: 1px solid var(--border); min-height: 0">
        {{ content }}
      </div>
    </div>

    <div v-else style="color: var(--text-muted); text-align: center; padding: 60px 0">
      暂无内容
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
      <el-button type="primary" @click="openInBrowser">在浏览器中打开</el-button>
    </template>
  </el-dialog>
</template>
