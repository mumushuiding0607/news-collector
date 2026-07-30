<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { deleteImportanceByScore } from "../../../api";

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "deleted"): void;
}>();

const score = ref(5);
const loading = ref(false);

watch(
  () => props.visible,
  (v) => {
    if (v) score.value = 5;
  }
);

async function handleConfirm() {
  try {
    await ElMessageBox.confirm(
      `确认删除评分低于 ${score.value} 分的所有重要新闻？此操作不可恢复！`,
      "删除确认",
      { type: "warning" }
    );
  } catch {
    return;
  }
  loading.value = true;
  try {
    const res = (await deleteImportanceByScore(score.value)) as { deleted?: number };
    ElMessage.success(`已删除 ${res.deleted || 0} 条记录`);
    emit("update:visible", false);
    emit("deleted");
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
    title="删除低分重要新闻"
    style="width: 95%; max-width: 400px"
  >
    <el-form label-position="top">
      <el-form-item label="最低分数（删除评分低于此值的新闻）">
        <el-input-number v-model="score" :min="0" :max="100" :step="1" style="width: 100%" />
      </el-form-item>
      <div style="color: var(--danger); font-size: 13px; margin-top: 8px">
        警告：将删除所有评分低于 {{ score }} 分的重要新闻，删除后无法恢复，请谨慎操作！
      </div>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="danger" :loading="loading" @click="handleConfirm">删除</el-button>
    </template>
  </el-dialog>
</template>
