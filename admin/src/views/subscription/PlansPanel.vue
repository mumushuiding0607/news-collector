<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { getSubscriptionTiers, updateSubscriptionTiers } from "../../api";
import { useMobile } from "../../composables/useMobile";

const { isMobile } = useMobile();

const loading = ref(false);
const tiers = ref<Record<string, unknown>[]>([]);
const editTiers = ref<Record<string, unknown>[]>([]);
const editMode = ref(false);
const saving = ref(false);

async function fetchTiers() {
  loading.value = true;
  try {
    const data = (await getSubscriptionTiers()) as { subscription_tiers?: Record<string, unknown>[] };
    tiers.value = data.subscription_tiers || [];
    editTiers.value = JSON.parse(JSON.stringify(tiers.value));
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function startEdit() {
  editTiers.value = JSON.parse(JSON.stringify(tiers.value));
  editMode.value = true;
}

function cancelEdit() {
  editTiers.value = [];
  editMode.value = false;
}

async function saveEdit() {
  saving.value = true;
  try {
    await updateSubscriptionTiers(editTiers.value as Record<string, unknown>[]);
    ElMessage.success("套餐已保存");
    editMode.value = false;
    await fetchTiers();
  } catch {
    // interceptor already shows popup
  } finally {
    saving.value = false;
  }
}

onMounted(fetchTiers);
</script>

<template>
  <div>
    <div v-if="!editMode" style="margin-bottom: 16px; text-align: right">
      <el-button type="primary" @click="startEdit">编辑套餐</el-button>
    </div>
    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px" v-loading="loading">
      <el-row v-if="!isMobile" :gutter="20">
        <el-col v-for="(plan, i) in tiers" :key="i" :span="8">
          <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; text-align: center">
            <div style="color: var(--gold); font-size: 18px; font-weight: bold">{{ plan.name }}</div>
            <div style="color: var(--text-h); font-size: 28px; font-weight: bold; margin: 12px 0">
              ¥{{ plan.price }}
              <span style="font-size: 12px; color: var(--text-muted)">/{{ plan.duration_days }}天</span>
            </div>
            <div style="color: var(--text); font-size: 13px">{{ plan.description }}</div>
            <div v-if="(plan.features as string[])" style="margin-top: 8px">
              <el-tag v-for="(f, fi) in (plan.features as string[])" :key="fi" size="small" style="margin: 2px">{{ f }}</el-tag>
            </div>
          </div>
        </el-col>
      </el-row>
      <div v-else>
        <div
          v-for="(plan, i) in tiers"
          :key="i"
          style="background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 12px; text-align: center"
        >
          <div style="color: var(--gold); font-size: 16px; font-weight: bold">{{ plan.name }}</div>
          <div style="color: var(--text-h); font-size: 24px; font-weight: bold; margin: 8px 0">
            ¥{{ plan.price }}
            <span style="font-size: 12px; color: var(--text-muted)">/{{ plan.duration_days }}天</span>
          </div>
          <div style="color: var(--text); font-size: 13px">{{ plan.description }}</div>
          <div v-if="(plan.features as string[])" style="margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap; justify-content: center">
            <el-tag v-for="(f, fi) in (plan.features as string[])" :key="fi" size="small">{{ f }}</el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <el-card v-if="editMode" style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
      <template #header>
        <span style="color: var(--gold)">编辑套餐</span>
      </template>
      <el-form label-width="100px" style="max-width: 800px">
        <el-table :data="editTiers" stripe style="color: var(--text); margin-bottom: 16px">
          <el-table-column label="等级" width="100">
            <template #default="{ row }">
              <el-tag :type="row.level === 'premium' ? 'warning' : row.level === 'pro' ? 'success' : 'info'">{{ row.level }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="名称">
            <template #default="{ row }">
              <el-input v-model="row.name" placeholder="套餐名称" />
            </template>
          </el-table-column>
          <el-table-column label="价格">
            <template #default="{ row }">
              <el-input-number v-model="row.price" :min="0" />
            </template>
          </el-table-column>
          <el-table-column label="天数">
            <template #default="{ row }">
              <el-input-number v-model="row.duration_days" :min="1" />
            </template>
          </el-table-column>
          <el-table-column label="描述">
            <template #default="{ row }">
              <el-input v-model="row.description" placeholder="描述" />
            </template>
          </el-table-column>
        </el-table>
        <div style="margin-top: 12px">
          <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
          <el-button @click="cancelEdit">取消</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>
