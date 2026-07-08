<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { createCrawlConfig } from "../../../api";
import { useNewsTypeStore } from "../../../stores/newsType";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "added"): void;
}>();

const form = ref({ name: "", url: "" });
const loading = ref(false);
const newsTypeStore = useNewsTypeStore();

watch(
  () => props.visible,
  (v) => {
    if (v) {
      form.value = { name: "", url: "" };
    }
  }
);

async function handleSubmit() {
  if (!form.value.url) {
    ElMessage.warning("请输入数据源 URL");
    return;
  }
  if (!form.value.name) {
    ElMessage.warning("请输入数据源名称");
    return;
  }
  loading.value = true;
  try {
    const newsType = newsTypeStore.newsType === "ai" ? "ai" : "stock";
    const result = await createCrawlConfig(
      { name: form.value.name, url_norm: form.value.url },
      newsType
    ) as { ok?: boolean; error?: string };
    if (!result.ok) {
      ElMessage.error(result.error || "新增失败");
      return;
    }
    ElMessage.success("新增成功");
    emit("added");
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
    title="新增数据源"
    style="width: 95%; max-width: 460px"
  >
    <el-form label-position="top">
      <el-form-item label="数据源名称" required>
        <el-input v-model="form.name" placeholder="如：CSDN资讯" />
      </el-form-item>
      <el-form-item label="数据源 URL" required>
        <el-input v-model="form.url" placeholder="https://example.com/news" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">新增</el-button>
    </template>
  </el-dialog>
</template>
