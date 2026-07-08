<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { learnSourceAsync } from "../../../api";
import { useNewsTypeStore } from "../../../stores/newsType";

const props = defineProps<{
  visible: boolean;
  initialRow: Record<string, unknown> | null;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "started", payload: { sourceName: string; logFile: string }): void;
}>();

const form = ref({ url: "", name: "", headline: "", skipArticle: false });
const loading = ref(false);
const newsTypeStore = useNewsTypeStore();

watch(
  () => props.visible,
  (v) => {
    if (v) {
      const row = props.initialRow;
      form.value = {
        url: row ? ((row.url_norm as string) || "") : "",
        name: row ? ((row.name as string) || "") : "",
        headline: "",
        skipArticle: false,
      };
    }
  }
);

async function handleSubmit() {
  const { url, name, headline, skipArticle } = form.value;
  if (!url) {
    ElMessage.warning("请输入数据源 URL");
    return;
  }
  try {
    await ElMessageBox.confirm(`确认对数据源「${name || url}」执行学习？`, "确认学习", { type: "info" });
  } catch {
    return;
  }
  loading.value = true;
  try {
    const newsType = newsTypeStore.newsType === "ai" ? "ai" : "stock";
    await learnSourceAsync({ url, name, headline, skip_article: skipArticle, news_type: newsType });
    ElMessage.success(`学习任务已启动：${name || url}`);
    emit("started", { sourceName: name || url, logFile: "list_discovery.log" });
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
    title="触发学习"
    style="width: 95%; max-width: 520px"
  >
    <el-form label-position="top">
      <el-form-item label="数据源 URL" required>
        <el-input v-model="form.url" placeholder="https://example.com/news" />
      </el-form-item>
      <el-form-item label="数据源名称（可选）">
        <el-input v-model="form.name" placeholder="如：CSDN资讯" />
      </el-form-item>
      <el-form-item label="已知标题（用于标题逆推，可选）">
        <el-input v-model="form.headline" placeholder="请输入一个已知新闻标题" />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.skipArticle">跳过正文抓取（仅学习列表配置）</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">开始学习</el-button>
    </template>
  </el-dialog>
</template>
