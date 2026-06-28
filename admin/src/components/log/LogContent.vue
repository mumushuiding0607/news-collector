<script setup lang="ts">
import { ref, watch, nextTick } from "vue";

const props = defineProps<{
  lines: string[];
  loading: boolean;
  isMobile: boolean;
}>();

const emit = defineEmits<{
  (e: "refresh"): void;
}>();

const logContainerRef = ref<HTMLElement | null>(null);

function lineColor(line: string): string {
  if (line.includes("ERROR")) return "var(--danger)";
  if (line.includes("WARNING")) return "var(--warning)";
  return "var(--text)";
}

watch(() => props.lines.length, async () => {
  await nextTick();
});
</script>

<template>
  <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column; min-width: 0">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
      <div style="color: var(--primary); font-size: 14px">
        日志内容
        <span style="color: var(--text-muted); font-size: 12px; margin-left: 12px">共 {{ lines.length }} 条</span>
      </div>
      <el-button size="small" @click="emit('refresh')" :loading="loading">刷新</el-button>
    </div>

    <div
      ref="logContainerRef"
      :style="isMobile
        ? 'flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 10px; font-family: monospace; font-size: 11px; line-height: 1.6; min-height: 150px'
        : 'flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 12px; font-family: monospace; font-size: 12px; line-height: 1.6; min-height: 200px'"
    >
      <div v-if="lines.length === 0 && !loading" style="color: var(--text-muted); text-align: center; padding: 40px">
        暂无日志内容
      </div>
      <div v-for="(line, i) in [...lines].reverse()" :key="i" style="white-space: pre-wrap; word-break: break-all">
        <span style="color: var(--text-muted); margin-right: 8px">{{ i + 1 }}</span>
        <span :style="`color: ${lineColor(line)}`">{{ line }}</span>
      </div>
    </div>
  </div>
</template>
