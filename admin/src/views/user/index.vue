<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getUsers, updateUserLevel } from "../../api";
import { MoreFilled } from "@element-plus/icons-vue";
import { useMobile } from "../../composables/useMobile";

const { isMobile } = useMobile();

const loading = ref(false);
const tableData = ref<Record<string, unknown>[]>([]);
const pagination = ref({ page: 1, limit: 20, total: 0 });
const filterForm = ref({ level: "", phone: "" });

async function fetchUsers() {
  loading.value = true;
  try {
    const params = {
      page: pagination.value.page,
      limit: pagination.value.limit,
      subscription_level: filterForm.value.level || undefined,
      phone: filterForm.value.phone || undefined,
    };
    const res = await getUsers(params) as { users?: Record<string, unknown>[]; total?: number };
    tableData.value = res.users || [];
    pagination.value.total = res.total || 0;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function handleSetLevel(id: number, level: string) {
  await updateUserLevel(id, level, 30);
  fetchUsers();
}

function handleSearch() {
  pagination.value.page = 1;
  fetchUsers();
}

onMounted(fetchUsers);
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">用户管理</h2>

    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="订阅等级">
          <el-select v-model="filterForm.level" placeholder="全部" clearable style="width: 140px">
            <el-option label="免费" value="free" />
            <el-option label="专业版" value="pro" />
            <el-option label="高级版" value="premium" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="filterForm.phone" placeholder="模糊搜索" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
      <!-- 桌面端表格 -->
      <div v-if="!isMobile" :style="{ overflowX: 'auto' }">
        <el-table :data="tableData" v-loading="loading" stripe style="color: var(--text); min-width: 700px">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="phone" label="手机号" width="140" />
          <el-table-column prop="nickname" label="昵称" width="100" />
          <el-table-column prop="email" label="邮箱" width="180" />
          <el-table-column prop="subscription_level" label="等级" width="90">
            <template #default="{ row }">
              <el-tag :type="row.subscription_level === 'premium' ? 'warning' : row.subscription_level === 'pro' ? 'success' : 'info'">
                {{ row.subscription_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="subscription_expire_at" label="过期时间" width="160" />
          <el-table-column prop="created_at" label="注册时间" width="160" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="success" link @click="handleSetLevel(row.id as number, 'pro')">Pro</el-button>
              <el-button size="small" type="warning" link @click="handleSetLevel(row.id as number, 'premium')">Premium</el-button>
              <el-button size="small" type="info" link @click="handleSetLevel(row.id as number, 'free')">Free</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 移动端卡片列表 -->
      <div v-else v-loading="loading">
        <div v-if="tableData.length === 0" style="color: var(--text-muted); text-align: center; padding: 40px">
          暂无数据
        </div>
        <div
          v-for="row in tableData"
          :key="row.id"
          style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px"
        >
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
            <div>
              <div style="color: var(--text); font-size: 14px; font-weight: 500">{{ row.nickname || '未设置昵称' }}</div>
              <div style="color: var(--text-muted); font-size: 12px; margin-top: 2px">{{ row.phone }}</div>
            </div>
            <el-tag :type="row.subscription_level === 'premium' ? 'warning' : row.subscription_level === 'pro' ? 'success' : 'info'" size="small">
              {{ row.subscription_level }}
            </el-tag>
          </div>
          <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 8px">{{ row.email }}</div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px">
            <div>
              <div style="color: var(--text-muted); font-size: 11px">注册：{{ row.created_at }}</div>
              <div style="color: var(--warning); font-size: 11px; margin-top: 2px">过期：{{ row.subscription_expire_at }}</div>
            </div>
            <el-dropdown trigger="click" @command="(cmd: string) => handleSetLevel(row.id as number, cmd)">
              <el-button size="small" type="primary">
                设置等级 <el-icon style="margin-left: 2px"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="pro">Pro</el-dropdown-item>
                  <el-dropdown-item command="premium">Premium</el-dropdown-item>
                  <el-dropdown-item command="free">Free</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 16px">
        <el-pagination
          v-model:current-page="pagination.page"
          :page-size="pagination.limit"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="fetchUsers"
        />
      </div>
    </el-card>
  </div>
</template>