<script setup lang="ts">
import { ref, watch } from "vue";
import { fetchArticleContent } from "../../../api";
import { useMobile } from "../../../composables/useMobile";

const { isMobile } = useMobile();

const props = defineProps<{
  visible: boolean;
  row: Record<string, unknown> | null;
  sourceName: string;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

const content = ref("");
const loading = ref(false);
const title = ref("");
const publishDate = ref("");

watch(
  () => [props.visible, props.row],
  async ([v, row]) => {
    if (v && row) {
      const r = row as Record<string, unknown>;
      const url = r.url as string;
      if (!url) {
        content.value = "文章 URL 为空";
        return;
      }
      title.value = (r.title as string) || "";
      publishDate.value = (r.time as string) || "";
      loading.value = true;
      content.value = "";
      try {
        const result = (await fetchArticleContent(url, props.sourceName)) as unknown as Record<string, unknown>;
        content.value = (result.content as string) || "";
        publishDate.value = (result.publish_date as string) || publishDate.value;
        if (!content.value) content.value = "未能获取到文章内容";
      } catch (e) {
        content.value = `获取失败: ${e}`;
      } finally {
        loading.value = false;
      }
    }
  }
);
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="(val: boolean) => emit('update:visible', val)"
    :title="title || '文章内容'"
    :fullscreen="isMobile"
    style="width: 95%; max-width: 800px"
  >
    <div v-loading="loading" style="max-height: 60vh; overflow-y: auto">
      <div v-if="publishDate" style="color: var(--text-muted); margin-bottom: 12px">发布时间：{{ publishDate }}</div>
      <div v-if="content" style="white-space: pre-wrap; line-height: 1.8">{{ content }}</div>
      <div v-else style="text-align: center; padding: 40px; color: var(--text-muted)">暂无内容</div>
    </div>
    <template #footer>
      <el-button @click="emit('update:visible', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>
