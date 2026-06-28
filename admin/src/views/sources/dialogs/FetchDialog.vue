<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { fetchSourceNews } from "../../../api";

const props = defineProps<{
  visible: boolean;
  initialUrl: string;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "fetched", payload: { url: string; sourceName: string; news: Record<string, unknown>[] }): void;
}>();

const form = ref({ url: "", limit: 10 });
const loading = ref(false);

watch(
  () => props.visible,
  (v) => {
    if (v) {
      form.value = { url: props.initialUrl || "", limit: 10 };
    }
  }
);

async function handleSubmit() {
  if (!form.value.url) {
    ElMessage.warning("请输入数据源 URL");
    return;
  }
  loading.value = true;
  try {
    const result = (await fetchSourceNews({ url: form.value.url, limit: form.value.limit })) as Record<string, unknown>;
    const news = (result.news as Record<string, unknown>[]) || [];
    emit("fetched", {
      url: form.value.url,
      sourceName: (result.source_name as string) || "",
      news,
    });
    emit("update:visible", false);
  } catch {
    // interceptor shows popup
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    title="抓取新闻列表"
    style="width: 95%; max-width: 460px"
  >
    <el-form label-position="top">
      <el-form-item label="数据源 URL" required>
        <el-input v-model="form.url" placeholder="https://example.com/news" />
      </el-form-item>
      <el-form-item label="抓取数量">
        <el-input-number v-model="form.limit" :min="1" :max="100" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">抓取</el-button>
    </template>
  </el-dialog>
</template>
