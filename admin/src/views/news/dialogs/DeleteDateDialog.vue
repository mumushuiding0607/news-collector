<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { deletePrimarySourcesByDate } from "../../../api";

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "deleted"): void;
}>();

const date = ref(new Date().toISOString().split("T")[0]);
const loading = ref(false);

watch(
  () => props.visible,
  (v) => {
    if (v) date.value = new Date().toISOString().split("T")[0];
  }
);

async function handleConfirm() {
  try {
    await ElMessageBox.confirm(`确认删除 ${date.value} 抓取的所有原始数据？此操作不可恢复！`, "删除确认", { type: "warning" });
  } catch {
    return;
  }
  loading.value = true;
  try {
    const res = (await deletePrimarySourcesByDate(date.value)) as { deleted?: number };
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
    title="删除原始数据"
    style="width: 95%; max-width: 400px"
  >
    <el-form label-position="top">
      <el-form-item label="抓取日期">
        <el-date-picker
          v-model="date"
          type="date"
          placeholder="选择日期"
          style="width: 100%"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      <div style="color: var(--danger); font-size: 13px; margin-top: 8px">警告：删除后无法恢复，请谨慎操作！</div>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="danger" :loading="loading" @click="handleConfirm">删除</el-button>
    </template>
  </el-dialog>
</template>
