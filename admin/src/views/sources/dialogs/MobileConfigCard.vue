<script setup lang="ts">
import { ArrowRight } from "@element-plus/icons-vue";

defineProps<{
  row: Record<string, unknown>;
}>();

const emit = defineEmits<{
  (e: "open-detail", row: Record<string, unknown>): void;
  (e: "learn", row: Record<string, unknown>): void;
  (e: "fetch", row: Record<string, unknown>): void;
  (e: "anomaly", row: Record<string, unknown>): void;
  (e: "confirm", id: number): void;
  (e: "unconfirm", id: number): void;
  (e: "delete", id: number): void;
}>();
</script>

<template>
  <div
    style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px"
  >
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
      <div style="flex: 1; margin-right: 8px; cursor: pointer" @click="emit('open-detail', row)">
        <div style="display: flex; align-items: center; margin-bottom: 4px">
          <span style="color: var(--primary); font-size: 14px; font-weight: 500">{{ row.name }}</span>
          <el-icon style="color: var(--primary); margin-left: 4px"><ArrowRight /></el-icon>
        </div>
        <div style="color: var(--text-muted); font-size: 12px; word-break: break-all">{{ row.url_norm }}</div>
      </div>
      <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px">
        <el-tag :type="row.checked ? 'success' : 'info'" size="small">{{ row.checked ? '已确认' : '未确认' }}</el-tag>
        <el-tag v-if="row.is_flash" type="warning" size="small">快讯</el-tag>
      </div>
    </div>
    <div style="display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap">
      <el-tag :type="row.source_type === 'api' ? 'primary' : row.source_type === 'ajax' ? 'warning' : 'info'" size="small">{{ row.source_type || 'html' }}</el-tag>
      <span v-if="row.list_config" style="color: var(--success); font-size: 12px">列表✓</span>
      <span v-if="row.content_extract" style="color: var(--success); font-size: 12px">正文✓</span>
      <span style="color: var(--text-muted); font-size: 12px">优先级{{ row.crawl_order }}</span>
    </div>
    <div style="display: flex; gap: 6px; flex-wrap: wrap">
      <el-button size="small" type="primary" @click="emit('learn', row)">学习</el-button>
      <el-button size="small" @click="emit('fetch', row)">抓取</el-button>
      <el-button size="small" type="warning" @click="emit('anomaly', row)">异动</el-button>
      <el-button v-if="!row.checked" size="small" type="success" @click="emit('confirm', row.id as number)">确认</el-button>
      <el-button v-else size="small" type="info" @click="emit('unconfirm', row.id as number)">取消</el-button>
      <el-button size="small" type="danger" @click="emit('delete', row.id as number)">删除</el-button>
    </div>
  </div>
</template>
