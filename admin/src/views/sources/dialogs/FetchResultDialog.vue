<script setup lang="ts">
import { useMobile } from "../../../composables/useMobile";

const { isMobile } = useMobile();

defineProps<{
  visible: boolean;
  data: Record<string, unknown>[];
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "fetch-article", row: Record<string, unknown>): void;
}>();
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    title="抓取结果"
    :fullscreen="isMobile"
    :width="isMobile ? '100%' : '800px'"
  >
    <div v-if="!isMobile" v-loading="loading" style="max-height: 70vh; overflow-y: auto">
      <el-table :data="data" stripe style="color: var(--text); width: 100%">
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <a v-if="row.url" :href="row.url as string" target="_blank" style="color: var(--primary)">{{ row.url }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间" width="160" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="emit('fetch-article', row)">抓取正文</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="data.length === 0 && !loading" style="text-align: center; padding: 40px; color: var(--text-muted)">暂无数据</div>
    </div>
    <div v-else v-loading="loading" style="max-height: 100%; overflow-y: auto; flex: 1">
      <div v-if="data.length === 0" style="text-align: center; padding: 20px; color: var(--text-muted)">暂无数据</div>
      <div
        v-for="row in data"
        :key="row.url as string"
        style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 10px"
      >
        <div style="margin-bottom: 8px">
          <div style="color: var(--text); font-size: 13px; font-weight: 500; margin-bottom: 4px; word-break: break-all">{{ row.title }}</div>
          <div style="color: var(--text-muted); font-size: 11px">{{ row.time }}</div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center">
          <a v-if="row.url" :href="row.url as string" target="_blank" style="color: var(--primary); font-size: 12px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
            {{ row.url }}
          </a>
          <el-button size="small" type="primary" @click="emit('fetch-article', row)">抓取正文</el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>
