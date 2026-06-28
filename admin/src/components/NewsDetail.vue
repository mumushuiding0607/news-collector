<script setup lang="ts">
import { ref, watch } from "vue";
import { getNewsDetail, getPrimarySourceDetail } from "../api";
import { useMobile } from "../composables/useMobile";

const { isMobile } = useMobile();

const props = defineProps<{
  visible: boolean;
  newsId: number | null;
  source?: "news" | "primary";
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

const loading = ref(false);
const newsData = ref<Record<string, unknown> | null>(null);

async function fetchDetail() {
  if (props.newsId === null) return;
  loading.value = true;
  try {
    if (props.source === "primary") {
      const res = await getPrimarySourceDetail(props.newsId) as unknown;
      newsData.value = res as Record<string, unknown>;
    } else {
      const res = await getNewsDetail(props.newsId) as unknown;
      newsData.value = res as Record<string, unknown>;
    }
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function close() {
  emit("update:visible", false);
}

watch(() => props.visible, (val) => {
  if (val && props.newsId) {
    fetchDetail();
  }
});
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="close"
    title="新闻详情"
    :fullscreen="isMobile"
    width="90%"
    style="max-width: 700px;"
    destroy-on-close
  >
    <div v-if="loading" style="text-align: center; padding: 40px">
      <el-icon class="is-loading" style="font-size: 24px"><Loading /></el-icon>
    </div>

    <div v-else-if="newsData" style="color: var(--text)">
      <div v-if="newsData.content" style="line-height: 1.8; max-height: 70vh; overflow-y: auto; white-space: pre-wrap;">
        {{ newsData.content }}
      </div>
      <div v-else style="color: var(--text-muted); text-align: center; padding: 40px">
        暂无正文内容
      </div>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>
  </el-dialog>
</template>