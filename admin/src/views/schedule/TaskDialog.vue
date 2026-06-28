<script setup lang="ts">
import { ref, watch } from "vue";
import { handlerOptions } from "./useScheduleTasks";

const props = defineProps<{
  visible: boolean;
  title: string;
  isEdit: boolean;
  initial: Record<string, unknown>;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "save", task: Record<string, unknown>, isEdit: boolean, currentId: string): void;
}>();

const form = ref({
  id: "",
  name: "",
  description: "",
  cron: "",
  enabled: true,
  handler: "",
});

const currentId = ref("");

watch(
  () => props.visible,
  (v) => {
    if (v) {
      form.value = {
        id: (props.initial.id as string) || "",
        name: (props.initial.name as string) || "",
        description: (props.initial.description as string) || "",
        cron: (props.initial.cron as string) || "",
        enabled: props.initial.enabled === undefined ? true : Boolean(props.initial.enabled),
        handler: (props.initial.handler as string) || "",
      };
      currentId.value = (props.initial.id as string) || "";
    }
  }
);

function handleSave() {
  emit("save", form.value, props.isEdit, currentId.value);
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    :title="title"
    style="width: 95%; max-width: 600px"
  >
    <el-form :model="form" label-width="100px" style="max-width: 500px">
      <el-form-item label="任务ID">
        <el-input v-model="form.id" :disabled="isEdit" placeholder="如: news_pipeline" />
      </el-form-item>
      <el-form-item label="名称">
        <el-input v-model="form.name" placeholder="任务显示名称" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="任务描述" />
      </el-form-item>
      <el-form-item label="Cron 表达式">
        <el-input v-model="form.cron" placeholder="30 8,11,14 * * 1-5" />
      </el-form-item>
      <el-form-item label="处理器">
        <el-select v-model="form.handler" placeholder="选择处理器" style="width: 100%">
          <el-option v-for="opt in handlerOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="启用">
        <el-switch v-model="form.enabled" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>
