<script setup lang="ts">
import { onMounted } from "vue";
import { useMobile } from "../../composables/useMobile";
import { usePendingUsers } from "./usePendingUsers";
import { getPlanPrice } from "./plans";

const { isMobile } = useMobile();
const { loading, list, fetchData, handleConfirm, handleReject } = usePendingUsers();

onMounted(fetchData);
</script>

<template>
  <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
    <template #header>
      <span style="color: var(--gold)">待确认订阅 ({{ list.length }})</span>
    </template>

    <div v-if="!isMobile && list.length > 0" :style="{ overflowX: 'auto' }">
      <el-table :data="list" v-loading="loading" stripe style="color: var(--text); min-width: 800px">
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="nickname" label="昵称" width="100" />
        <el-table-column prop="level" label="订阅等级" width="100">
          <template #default="{ row }">
            <el-tag :type="row.level === 'premium' ? 'warning' : 'success'">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="价格" width="100">
          <template #default="{ row }">
            <span style="color: var(--gold)">¥{{ getPlanPrice(row.level as string) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_at" label="开始时间" width="160" />
        <el-table-column prop="end_at" label="到期时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" link @click="handleConfirm(row.user_id as number)">确认</el-button>
            <el-button size="small" type="danger" link @click="handleReject(row.user_id as number)">撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-else-if="isMobile && list.length > 0" v-loading="loading">
      <div
        v-for="row in list"
        :key="row.user_id as number"
        style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px"
      >
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
          <div>
            <div style="color: var(--text); font-size: 14px; font-weight: 500">{{ row.nickname || '未设置昵称' }}</div>
            <div style="color: var(--text-muted); font-size: 12px; margin-top: 2px">{{ row.phone }}</div>
          </div>
          <el-tag :type="row.level === 'premium' ? 'warning' : 'success'" size="small">{{ row.level }}</el-tag>
        </div>
        <div style="color: var(--gold); font-size: 14px; margin-bottom: 8px">¥{{ getPlanPrice(row.level as string) }}</div>
        <div style="display: flex; gap: 8px; font-size: 12px; color: var(--text-muted); margin-bottom: 10px">
          <span>{{ row.start_at }}</span>
          <span>→</span>
          <span>{{ row.end_at }}</span>
        </div>
        <div style="display: flex; gap: 8px">
          <el-button size="small" type="success" style="flex: 1" @click="handleConfirm(row.user_id as number)">确认</el-button>
          <el-button size="small" type="danger" style="flex: 1" @click="handleReject(row.user_id as number)">撤销</el-button>
        </div>
      </div>
    </div>

    <div v-else style="color: var(--text-muted); text-align: center; padding: 40px">暂无待确认的用户</div>
  </el-card>
</template>
