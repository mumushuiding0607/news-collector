<script setup lang="ts">
import { ref, watch } from "vue";
import { getAnomalyNews } from "../../../api";

const props = defineProps<{
  visible: boolean;
  sourceName: string;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

const data = ref<Record<string, unknown>[]>([]);
const loading = ref(false);

watch(
  () => props.visible,
  async (v) => {
    if (v && props.sourceName) {
      loading.value = true;
      data.value = [];
      try {
        const res = await getAnomalyNews({ sourceName: props.sourceName, limit: 100 }) as { list?: Record<string, unknown>[] };
        // 按 id 降序
        const list = res.list || [];
        list.sort((a, b) => (b.id as number) - (a.id as number));
        data.value = list;
      } catch (e) {
        console.error(e);
      } finally {
        loading.value = false;
      }
    }
  }
);
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    :title="`异动消息 - ${sourceName}`"
    style="width: 95%; max-width: 700px"
  >
    <el-table :data="data" v-loading="loading" stripe style="color: var(--text)" max-height="400">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="标题" min-width="200">
        <template #default="{ row }">
          <a v-if="row.url" :href="row.url as string" target="_blank" style="color: var(--primary)">{{ row.title }}</a>
          <span v-else>{{ row.title }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="source_name" label="数据源" width="120" show-overflow-tooltip />
      <el-table-column prop="publish_time" label="发布时间" width="160" />
      <el-table-column prop="processed" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.processed ? 'success' : 'warning'" size="small">
            {{ row.processed ? '已处理' : '未处理' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="data.length === 0 && !loading" style="text-align: center; padding: 20px; color: var(--text-muted)">
      暂无异动消息
    </div>
  </el-dialog>
</template>
