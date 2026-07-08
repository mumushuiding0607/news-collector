<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getCrawlConfigs, confirmCrawlConfig, unconfirmCrawlConfig, deleteCrawlConfig } from "../../api";
import { useMobile } from "../../composables/useMobile";
import { useNewsTypeStore } from "../../stores/newsType";
import ConfigDetailDialog from "./dialogs/ConfigDetailDialog.vue";
import MobileConfigCard from "./dialogs/MobileConfigCard.vue";

const { isMobile } = useMobile();
const newsTypeStore = useNewsTypeStore();

const data = ref<Record<string, unknown>[]>([]);
const loading = ref(false);
const pagination = ref({ page: 1, limit: 10, total: 0 });
const filterChecked = ref<number | "">("");

const detailVisible = ref(false);
const detailRow = ref<Record<string, unknown> | null>(null);

const emit = defineEmits<{
  (e: "learn", row: Record<string, unknown>): void;
  (e: "fetch", row: Record<string, unknown>): void;
  (e: "anomaly", row: Record<string, unknown>): void;
}>();

async function fetchData() {
  loading.value = true;
  try {
    const newsType = newsTypeStore.newsType === "ai" ? "ai" : "stock";
    const params: Record<string, unknown> = {
      page: pagination.value.page,
      limit: pagination.value.limit,
      news_type: newsType,
    };
    if (filterChecked.value !== "") {
      params.checked = filterChecked.value;
    }
    const res = (await getCrawlConfigs(params)) as { list?: Record<string, unknown>[]; total?: number };
    data.value = res.list || [];
    pagination.value.total = res.total || 0;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function handleConfirm(id: number) {
  try {
    const newsType = newsTypeStore.newsType === "ai" ? "ai" : "stock";
    await confirmCrawlConfig(id, newsType);
    ElMessage.success("已确认");
    fetchData();
  } catch {
    // interceptor shows popup
  }
}

async function handleUnconfirm(id: number) {
  try {
    const newsType = newsTypeStore.newsType === "ai" ? "ai" : "stock";
    await unconfirmCrawlConfig(id, newsType);
    ElMessage.success("已取消确认");
    fetchData();
  } catch {
    // interceptor shows popup
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm("确认删除该数据源？", "删除确认", { type: "warning" });
    const newsType = newsTypeStore.newsType === "ai" ? "ai" : "stock";
    await deleteCrawlConfig(id, newsType);
    ElMessage.success("删除成功");
    fetchData();
  } catch {
    // user cancel or interceptor error
  }
}

function openDetail(row: Record<string, unknown>) {
  detailRow.value = row;
  detailVisible.value = true;
}

function handleFilterChange() {
  pagination.value.page = 1;
  fetchData();
}

onMounted(fetchData);

defineExpose({ refresh: fetchData });
</script>

<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
      <el-form :inline="true">
        <el-form-item label="确认状态">
          <el-select v-model="filterChecked" placeholder="全部" clearable style="width: 140px" @change="handleFilterChange">
            <el-option label="未确认" :value="0" />
            <el-option label="已确认" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilterChange">筛选</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
      <div v-if="!isMobile" :style="{ overflowX: 'auto' }">
        <el-table :data="data" v-loading="loading" stripe style="color: var(--text); min-width: 900px">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="名称" min-width="120">
            <template #default="{ row }">
              <el-button type="primary" link @click="openDetail(row)">{{ row.name }}</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="url_norm" label="URL" min-width="200" show-overflow-tooltip />
          <el-table-column prop="source_type" label="类型" width="80">
            <template #default="{ row }">
              <el-tag :type="row.source_type === 'api' ? 'primary' : row.source_type === 'ajax' ? 'warning' : 'info'">
                {{ row.source_type || 'html' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_flash" label="快讯" width="70">
            <template #default="{ row }">
              <el-tag v-if="row.is_flash" type="warning" size="small">是</el-tag>
              <span v-else style="color: var(--text-muted)">否</span>
            </template>
          </el-table-column>
          <el-table-column prop="checked" label="确认" width="70">
            <template #default="{ row }">
              <el-tag :type="row.checked ? 'success' : 'info'" size="small">
                {{ row.checked ? '已确认' : '未确认' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="crawl_order" label="优先级" width="70" />
          <el-table-column prop="list_config" label="列表配置" width="100" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.list_config" style="color: var(--success)">有</span>
              <span v-else style="color: var(--text-muted)">无</span>
            </template>
          </el-table-column>
          <el-table-column prop="content_extract" label="正文配置" width="100" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.content_extract" style="color: var(--success)">有</span>
              <span v-else style="color: var(--text-muted)">无</span>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="160" />
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="emit('learn', row)">学习</el-button>
              <el-button size="small" link @click="emit('fetch', row)">抓取</el-button>
              <el-button size="small" type="warning" link @click="emit('anomaly', row)">异动</el-button>
              <el-button v-if="!row.checked" size="small" type="success" link @click="handleConfirm(row.id as number)">确认</el-button>
              <el-button v-else size="small" type="info" link @click="handleUnconfirm(row.id as number)">取消确认</el-button>
              <el-button size="small" type="danger" link @click="handleDelete(row.id as number)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-else v-loading="loading">
        <div v-if="data.length === 0" style="color: var(--text-muted); text-align: center; padding: 40px">暂无数据</div>
        <MobileConfigCard
          v-for="row in data"
          :key="row.id as number"
          :row="row"
          @open-detail="openDetail"
          @learn="(r) => emit('learn', r)"
          @fetch="(r) => emit('fetch', r)"
          @anomaly="(r) => emit('anomaly', r)"
          @confirm="handleConfirm"
          @unconfirm="handleUnconfirm"
          @delete="handleDelete"
        />
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 16px">
        <el-pagination
          v-model:current-page="pagination.page"
          :page-size="pagination.limit"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <ConfigDetailDialog v-model:visible="detailVisible" :row="detailRow" @saved="fetchData" />
  </div>
</template>
