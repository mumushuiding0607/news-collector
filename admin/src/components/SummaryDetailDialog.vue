<script setup lang="ts">
import { useMobile } from "../composables/useMobile";

const { isMobile } = useMobile();

defineProps<{
  visible: boolean;
  detail: Record<string, unknown>;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    :title="`简报 ${detail.date || ''}`"
    :fullscreen="isMobile"
    style="width: 95%; max-width: 800px"
  >
    <div v-if="detail.content" style="color: var(--text); line-height: 1.8; white-space: pre-wrap; max-height: 60vh; overflow-y: auto">
      <div v-if="(detail.content as Record<string, unknown>).summary" style="margin-bottom: 16px">
        <strong>摘要：</strong>{{ (detail.content as Record<string, unknown>).summary }}
      </div>
      <div v-if="(detail.content as Record<string, unknown>).main_stimulus" style="margin-bottom: 16px">
        <strong>核心刺激：</strong>{{ (detail.content as Record<string, unknown>).main_stimulus }}
      </div>
      <div v-if="(detail.content as Record<string, unknown>).correlation" style="margin-bottom: 16px">
        <strong>关联板块：</strong>{{ (detail.content as Record<string, unknown>).correlation }}
      </div>
      <div v-if="(detail.content as Record<string, unknown>).insights">
        <strong>洞察：</strong>{{ (detail.content as Record<string, unknown>).insights }}
      </div>
    </div>
    <div v-else style="color: var(--text-muted)">暂无内容</div>
  </el-dialog>
</template>
