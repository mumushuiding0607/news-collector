<script setup lang="ts">
import { ArrowRight } from "@element-plus/icons-vue";
import { useMobile } from "../../composables/useMobile";

const { isMobile } = useMobile();

defineProps<{
  data: Record<string, unknown>[];
  loading: boolean;
  mode: "comments" | "feedback";
  page: number;
  limit: number;
  total: number;
}>();

const emit = defineEmits<{
  (e: "open-news", newsId: number): void;
  (e: "page-change", page: number): void;
}>();

function contentField(row: Record<string, unknown>, mode: string): string {
  if (mode === "comments") return (row.content as string) || "";
  return (row.feedback_content as string) || "";
}
</script>

<template>
  <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
    <!-- 桌面端 -->
    <div v-if="!isMobile" :style="{ overflowX: 'auto' }">
      <el-table :data="data" v-loading="loading" stripe style="color: var(--text); min-width: 600px">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="news_title" label="新闻标题" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button type="primary" link @click="emit('open-news', row.news_id as number)">
              {{ row.news_title || `新闻 #${row.news_id}` }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column :prop="mode === 'comments' ? 'content' : 'feedback_content'" :label="mode === 'comments' ? '评论内容' : '反馈内容'" show-overflow-tooltip />
        <el-table-column v-if="mode === 'comments'" prop="processed" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.processed === 1 ? 'success' : 'warning'">
              {{ row.processed === 1 ? '已处理' : '未处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160" />
      </el-table>
    </div>

    <!-- 移动端 -->
    <div v-else v-loading="loading">
      <div v-if="data.length === 0" style="color: var(--text-muted); text-align: center; padding: 40px">暂无数据</div>
      <div
        v-for="row in data"
        :key="row.id as number"
        style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px; cursor: pointer"
        @click="emit('open-news', row.news_id as number)"
      >
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
          <div style="flex: 1">
            <div style="display: flex; align-items: center; margin-bottom: 6px">
              <span style="color: var(--primary); font-size: 14px; font-weight: 500">
                {{ row.news_title || `新闻 #${row.news_id}` }}
              </span>
              <el-icon style="color: var(--primary); margin-left: 4px"><ArrowRight /></el-icon>
            </div>
            <div style="color: var(--text); font-size: 14px; line-height: 1.5">{{ contentField(row, mode) }}</div>
          </div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px">
          <div v-if="mode === 'comments'" style="display: flex; gap: 8px; align-items: center">
            <el-tag :type="row.processed === 1 ? 'success' : 'warning'" size="small">
              {{ row.processed === 1 ? '已处理' : '未处理' }}
            </el-tag>
            <span style="color: var(--text-muted); font-size: 12px">{{ row.created_at }}</span>
          </div>
          <span v-else style="color: var(--text-muted); font-size: 12px">{{ row.created_at }}</span>
        </div>
      </div>
    </div>

    <div style="display: flex; justify-content: flex-end; margin-top: 16px">
      <el-pagination
        :current-page="page"
        :page-size="limit"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="(p: number) => emit('page-change', p)"
      />
    </div>
  </el-card>
</template>
