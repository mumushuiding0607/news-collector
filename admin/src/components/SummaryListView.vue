<script setup lang="ts">
import { onMounted } from "vue";
import { useMobile } from "../composables/useMobile";
import { useSummaryList } from "../composables/useSummaryList";
import SummaryDetailDialog from "./SummaryDetailDialog.vue";

const props = defineProps<{ type: string }>();

const { isMobile } = useMobile();
const { loading, list, pagination, detail, detailVisible, fetchList, openDetail, onPageChange } = useSummaryList(props.type);

onMounted(fetchList);
</script>

<template>
  <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
    <div v-if="!isMobile">
      <el-table :data="list" v-loading="loading" stripe style="color: var(--text)">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column prop="created_at" label="生成时间" width="160" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openDetail(row.date as string)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div v-else v-loading="loading">
      <div v-if="list.length === 0" style="color: var(--text-muted); text-align: center; padding: 40px">暂无数据</div>
      <div
        v-for="row in list"
        :key="row.date as string"
        style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px"
      >
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
          <span style="font-weight: 500">{{ row.date }}</span>
          <el-button size="small" type="primary" link @click="openDetail(row.date as string)">查看</el-button>
        </div>
        <div style="color: var(--text-muted); font-size: 12px">{{ row.type }} · {{ row.created_at }}</div>
      </div>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; flex-wrap: wrap; gap: 8px">
      <div style="display: flex; gap: 8px; flex-wrap: wrap">
        <slot name="actions" />
      </div>
      <el-pagination
        v-model:current-page="pagination.page"
        :page-size="pagination.limit"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @current-change="onPageChange"
      />
    </div>

    <SummaryDetailDialog v-model:visible="detailVisible" :detail="detail" />
  </el-card>
</template>
