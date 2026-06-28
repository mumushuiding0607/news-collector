<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { getCrawlConfigSourceNames } from "../../api";
import { MoreFilled, ArrowRight } from "@element-plus/icons-vue";
import { useMobile } from "../../composables/useMobile";
import { useNewsList } from "./useNewsList";
import type { NewsTab } from "./types";
import DeleteDateDialog from "./dialogs/DeleteDateDialog.vue";

const props = defineProps<{ tab: NewsTab; pipelineSteps: { step: number; name: string; desc: string; logFile: string }[] }>();
const emit = defineEmits<{
  (e: "open-pipeline", step: number, desc: string): void;
  (e: "open-detail", id: number): void;
}>();

const { isMobile } = useMobile();
const { loading, tableData, pagination, filterForm, fetchList, markUseful, handleSearch, handleReset } = useNewsList();

const sourceNameOptions = ref<string[]>([]);
const deleteDateVisible = ref(false);

async function fetchSourceNames() {
  try {
    const res = (await getCrawlConfigSourceNames()) as { source_names?: string[] };
    sourceNameOptions.value = res.source_names || [];
  } catch (e) {
    console.error(e);
  }
}

async function refresh() {
  await fetchList(props.tab);
}

async function handleMark(id: number, useful: boolean) {
  await markUseful(id, useful);
  await refresh();
}

async function doSearch() {
  handleSearch();
  await refresh();
}

function doReset() {
  handleReset();
  refresh();
}

watch(() => props.tab, refresh, { immediate: false });

onMounted(async () => {
  await fetchSourceNames();
  await refresh();
});

defineExpose({ refresh });
</script>

<template>
  <div>
    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px; padding: 12px 16px">
      <div v-if="!isMobile" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
        <el-select v-model="filterForm.status" placeholder="状态" clearable style="width: 120px">
          <el-option label="新稿件" value="new" />
          <el-option label="已读" value="read" />
          <el-option label="已评分" value="scored" />
          <el-option label="已推送" value="pushed" />
          <el-option label="异常" value="error" />
        </el-select>
        <el-select v-model="filterForm.source_name" placeholder="来源" clearable filterable style="width: 160px">
          <el-option v-for="name in sourceNameOptions" :key="name" :label="name" :value="name" />
        </el-select>
        <el-button type="primary" @click="doSearch">搜索</el-button>
        <el-button @click="doReset">重置</el-button>
        <div style="flex: 1" />
        <el-button v-if="tab === 'primary'" type="danger" @click="deleteDateVisible = true">删除指定日期</el-button>
        <el-dropdown v-if="pipelineSteps.length > 0" trigger="click" @command="(cmd: number) => { const s = pipelineSteps.find(p => p.step === cmd); if (s) emit('open-pipeline', s.step, s.desc) }">
          <el-button type="success">
            执行步骤 <el-icon class="el-icon--right"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="s in pipelineSteps" :key="s.step" :command="s.step">
                Step {{ s.step }} - {{ s.desc }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div v-else style="display: flex; flex-direction: column; gap: 10px">
        <el-select v-model="filterForm.source_name" placeholder="来源筛选" clearable filterable style="width: 100%">
          <el-option v-for="name in sourceNameOptions" :key="name" :label="name" :value="name" />
        </el-select>
        <el-select v-model="filterForm.status" placeholder="状态筛选" clearable style="width: 100%">
          <el-option label="新稿件" value="new" />
          <el-option label="已读" value="read" />
          <el-option label="已评分" value="scored" />
          <el-option label="已推送" value="pushed" />
          <el-option label="异常" value="error" />
        </el-select>
        <div style="display: flex; gap: 8px">
          <el-button type="primary" style="flex: 1" @click="doSearch">搜索</el-button>
          <el-button style="flex: 1" @click="doReset">重置</el-button>
        </div>
        <div style="display: flex; gap: 8px">
          <el-button v-if="tab === 'primary'" type="danger" style="flex: 1" @click="deleteDateVisible = true">删除指定日期</el-button>
          <el-dropdown v-if="pipelineSteps.length > 0" trigger="click" style="flex: 1" @command="(cmd: number) => { const s = pipelineSteps.find(p => p.step === cmd); if (s) emit('open-pipeline', s.step, s.desc) }">
            <el-button type="success" style="width: 100%">
              执行步骤 <el-icon class="el-icon--right"><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="s in pipelineSteps" :key="s.step" :command="s.step">
                  Step {{ s.step }} - {{ s.desc }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-card>

    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
      <div v-if="!isMobile" :style="{ overflowX: 'auto' }">
        <el-table :data="tableData" v-loading="loading" stripe style="color: var(--text); min-width: 600px">
          <template v-if="tab === 'importance'">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column label="标题" min-width="200">
              <template #default="{ row }">
                <el-button type="primary" link @click="emit('open-detail', row.id as number)">{{ row.title }}</el-button>
              </template>
            </el-table-column>
            <el-table-column prop="source_name" label="来源" width="120" />
            <el-table-column prop="publish_time" label="发布时间" width="160" />
            <el-table-column prop="importance_score" label="评分" width="80">
              <template #default="{ row }">
                <el-tag :type="Number(row.importance_score) >= 6 ? 'danger' : 'info'">{{ row.importance_score ?? 0 }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'pushed' ? 'success' : 'info'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="is_useful" label="评估" width="80">
              <template #default="{ row }">
                <span v-if="row.is_useful === 1" style="color: var(--success)">有用</span>
                <span v-else-if="row.is_useful === -1" style="color: var(--danger)">无用</span>
                <span v-else style="color: var(--text-muted)">未评估</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" link @click="handleMark(row.id as number, true)">有用</el-button>
                <el-button size="small" type="danger" link @click="handleMark(row.id as number, false)">无用</el-button>
              </template>
            </el-table-column>
          </template>
          <template v-else>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column label="标题" min-width="200">
              <template #default="{ row }">
                <div style="word-break: break-all; white-space: normal;">{{ row.title }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="source_name" label="来源" width="120" />
            <el-table-column prop="publish_time" label="发布时间" width="160" />
            <el-table-column prop="fetched_at" label="抓取时间" width="160" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'pushed' ? 'success' : 'info'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="content_length" label="内容长度" width="100">
              <template #default="{ row }">
                <span style="color: var(--text-muted)">{{ row.content_length || 0 }} 字</span>
              </template>
            </el-table-column>
          </template>
        </el-table>
      </div>

      <div v-else v-loading="loading">
        <div v-if="tableData.length === 0" style="color: var(--text-muted); text-align: center; padding: 40px">暂无数据</div>
        <div
          v-for="row in tableData"
          :key="row.id as number"
          style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px"
        >
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
            <div style="flex: 1; margin-right: 8px; cursor: pointer" @click="emit('open-detail', row.id as number)">
              <div :style="tab === 'importance' ? 'color: var(--primary)' : 'color: var(--text)'" style="font-size: 14px; font-weight: 500; line-height: 1.4; margin-bottom: 6px; word-break: break-all; white-space: normal;">
                {{ row.title }}
                <el-icon v-if="tab === 'importance'" style="margin-left: 4px; vertical-align: middle"><ArrowRight /></el-icon>
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center">
                <el-tag :type="row.status === 'pushed' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
                <span v-if="row.importance_score" style="color: var(--danger); font-size: 12px">评分: {{ row.importance_score }}</span>
                <span style="color: var(--text-muted); font-size: 12px">{{ row.source_name }}</span>
              </div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-muted); font-size: 12px">{{ tab === 'importance' ? row.publish_time : row.fetched_at }}</span>
            <el-button v-if="tab === 'importance'" type="primary" link size="small" @click.stop="emit('open-detail', row.id as number)">查看详情</el-button>
          </div>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 16px">
        <el-pagination
          v-model:current-page="pagination.page"
          :page-size="pagination.limit"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="refresh"
        />
      </div>
    </el-card>

    <DeleteDateDialog v-model:visible="deleteDateVisible" @deleted="refresh" />
  </div>
</template>
