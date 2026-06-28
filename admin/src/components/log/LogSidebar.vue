<script setup lang="ts">
defineProps<{
  dates: string[];
  files: Record<string, unknown>[];
  selectedDate: string;
  selectedFile: Record<string, unknown> | null;
  loading: boolean;
  isMobile: boolean;
}>();

const emit = defineEmits<{
  (e: "update:selectedDate", value: string): void;
  (e: "select-file", file: Record<string, unknown>): void;
}>();

function onDateChange(value: string) {
  emit("update:selectedDate", value);
}
</script>

<template>
  <!-- 桌面端：纵向侧栏 -->
  <div v-if="!isMobile" style="width: 220px; flex-shrink: 0; border-right: 1px solid var(--border); padding-right: 16px; overflow-y: auto">
    <div style="margin-bottom: 12px">
      <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 6px">日期</div>
      <el-select :model-value="selectedDate" placeholder="选择日期" style="width: 100%" :disabled="loading" @change="onDateChange">
        <el-option v-for="d in dates" :key="d" :label="d" :value="d" />
      </el-select>
    </div>

    <div v-loading="loading">
      <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 6px">日志文件 ({{ files.length }})</div>
      <div
        v-for="f in files"
        :key="f.path as string"
        @click="emit('select-file', f)"
        style="padding: 8px; cursor: pointer; border-radius: 4px; margin-bottom: 4px"
        :style="selectedFile?.path === f.path ? 'background: var(--primary-light)' : ''"
      >
        <div style="color: var(--text); font-size: 13px">{{ f.name }}</div>
        <div style="color: var(--text-muted); font-size: 11px">
          {{ f.size_display }} · {{ f.modified }}
        </div>
      </div>
    </div>
  </div>

  <!-- 移动端：上下排列的 select -->
  <div v-else style="display: flex; flex-direction: column; gap: 8px">
    <div>
      <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 4px">日期</div>
      <el-select :model-value="selectedDate" placeholder="选择日期" style="width: 100%" :disabled="loading" @change="onDateChange">
        <el-option v-for="d in dates" :key="d" :label="d" :value="d" />
      </el-select>
    </div>
    <div v-if="files.length > 0">
      <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 4px">日志文件</div>
      <el-select
        :model-value="selectedFile?.path as string"
        @change="(val: string) => { const f = files.find(f => f.path === val); if (f) emit('select-file', f) }"
        placeholder="选择文件"
        style="width: 100%"
        :disabled="loading"
      >
        <el-option v-for="f in files" :key="f.path as string" :label="f.name as string" :value="f.path as string" />
      </el-select>
    </div>
  </div>
</template>
