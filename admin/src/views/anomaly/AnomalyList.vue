<script setup lang="ts">
import { ref, onMounted } from "vue";
import { MoreFilled } from "@element-plus/icons-vue";
import { useMobile } from "../../composables/useMobile";
import { useAnomalyList } from "./useAnomalyList";
import { useAnomalyPipelines } from "./useAnomalyPipelines";
import { newsPipelineSteps, sourcePipelineSteps } from "./pipelineConfig";
import UrlPreviewDialog from "../../components/UrlPreviewDialog.vue";
import DeleteAnomalyBeforeDialog from "../../views/news/dialogs/DeleteAnomalyBeforeDialog.vue";

const { isMobile } = useMobile();
const {
  loading,
  tableData,
  pagination,
  filterForm,
  fetchData,
  handleDelete,
  handleMarkProcessed,
  handleSearch,
  handleReset,
  handlePageChange,
} = useAnomalyList();

const emit = defineEmits<{
  (e: "open-log", title: string, file: string): void;
}>();

const pipelines = useAnomalyPipelines(emit);

const previewVisible = ref(false);
const previewUrl = ref("");
const deleteBeforeVisible = ref(false);

function openPreview(url: string) {
  previewUrl.value = url;
  previewVisible.value = true;
}

onMounted(fetchData);

defineExpose({ refresh: fetchData });
</script>

<template>
  <div>
    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px; padding: 12px 16px">
      <div v-if="!isMobile" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
        <el-input v-model="filterForm.title" placeholder="标题" clearable style="width: 160px" />
        <el-input v-model="filterForm.source_name" placeholder="数据源名称" clearable style="width: 160px" />
        <el-input v-model="filterForm.keyword" placeholder="关键词（搜标题+内容）" clearable style="width: 200px" />
        <el-select v-model="filterForm.processed" placeholder="处理状态" clearable style="width: 120px">
          <el-option label="未处理" value="0" />
          <el-option label="已处理" value="1" />
        </el-select>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
        <div style="flex: 1" />
        <el-dropdown trigger="click" @command="(cmd: number) => { if (cmd === 0) { pipelines.runNewsFull() } else { const s = newsPipelineSteps.find(p => p.step === cmd); if (s) pipelines.runNewsStep(s.step, s.desc) } }">
          <el-button type="success">
            消息步骤 <el-icon class="el-icon--right"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item :command="0">完整执行</el-dropdown-item>
              <el-dropdown-item v-for="s in newsPipelineSteps" :key="s.step" :command="s.step">Step {{ s.step }} - {{ s.desc }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" @command="(cmd: number) => { const s = sourcePipelineSteps.find(p => p.step === cmd); if (s) pipelines.runSourceStep(s.step, s.desc) }">
          <el-button type="warning">
            数据源步骤 <el-icon class="el-icon--right"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="s in sourcePipelineSteps" :key="s.step" :command="s.step">Step {{ s.step }} - {{ s.desc }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="danger" @click="deleteBeforeVisible = true">删除日期之前</el-button>
      </div>
      <div v-else style="display: flex; flex-direction: column; gap: 10px">
        <el-input v-model="filterForm.title" placeholder="标题" clearable />
        <el-input v-model="filterForm.source_name" placeholder="数据源名称" clearable />
        <el-input v-model="filterForm.keyword" placeholder="关键词（搜标题+内容）" clearable />
        <el-select v-model="filterForm.processed" placeholder="处理状态" clearable style="width: 100%">
          <el-option label="未处理" value="0" />
          <el-option label="已处理" value="1" />
        </el-select>
        <div style="display: flex; gap: 8px">
          <el-button type="primary" style="flex: 1" @click="handleSearch">搜索</el-button>
          <el-button style="flex: 1" @click="handleReset">重置</el-button>
        </div>
        <el-dropdown trigger="click" style="width: 100%" @command="(cmd: number) => { if (cmd === 0) { pipelines.runNewsFull() } else { const s = newsPipelineSteps.find(p => p.step === cmd); if (s) pipelines.runNewsStep(s.step, s.desc) } }">
          <el-button type="success" style="width: 100%">
            消息步骤 <el-icon class="el-icon--right"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item :command="0">完整执行</el-dropdown-item>
              <el-dropdown-item v-for="s in newsPipelineSteps" :key="s.step" :command="s.step">Step {{ s.step }} - {{ s.desc }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" style="width: 100%" @command="(cmd: number) => { const s = sourcePipelineSteps.find(p => p.step === cmd); if (s) pipelines.runSourceStep(s.step, s.desc) }">
          <el-button type="warning" style="width: 100%">
            数据源步骤 <el-icon class="el-icon--right"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="s in sourcePipelineSteps" :key="s.step" :command="s.step">Step {{ s.step }} - {{ s.desc }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="danger" style="width: 100%" @click="deleteBeforeVisible = true">删除日期之前</el-button>
      </div>
    </el-card>

    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
      <div v-if="!isMobile">
        <el-table :data="tableData" v-loading="loading" stripe style="color: var(--text); min-width: 600px">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column label="标题" min-width="200">
            <template #default="{ row }">
              <el-button type="primary" link @click="openPreview(row.url as string)">{{ row.title }}</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="source_name" label="数据源" width="120" />
          <el-table-column prop="publish_time" label="发布时间" width="160" />
          <el-table-column prop="processed" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.processed === 1 ? 'success' : 'danger'">
                {{ row.processed === 1 ? "已确认" : "未确认" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="success" link @click="handleMarkProcessed(row.id as number)">确认</el-button>
              <el-button size="small" type="danger" link @click="handleDelete(row.id as number)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-else v-loading="loading">
        <div v-if="tableData.length === 0" style="color: var(--text-muted); text-align: center; padding: 40px">暂无数据</div>
        <div
          v-for="row in tableData"
          :key="row.id as number"
          style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px"
        >
          <div style="margin-bottom: 8px">
            <el-button type="primary" link style="font-size: 14px; font-weight: 500; word-break: break-all; white-space: normal; text-align: left" @click="openPreview(row.url as string)">{{ row.title }}</el-button>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px">
            <el-tag :type="row.processed === 1 ? 'success' : 'danger'" size="small">
              {{ row.processed === 1 ? "已确认" : "未确认" }}
            </el-tag>
            <span style="color: var(--text-muted); font-size: 12px">{{ row.source_name }}</span>
            <span style="color: var(--text-muted); font-size: 12px">{{ row.publish_time }}</span>
          </div>
          <div style="display: flex; gap: 8px">
            <el-button size="small" type="success" @click="handleMarkProcessed(row.id as number)">确认</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id as number)">删除</el-button>
          </div>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 16px">
        <el-pagination
          v-model:current-page="pagination.page"
          :page-size="pagination.limit"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <UrlPreviewDialog v-model:visible="previewVisible" :url="previewUrl" />
    <DeleteAnomalyBeforeDialog v-model:visible="deleteBeforeVisible" @deleted="fetchData" />
  </div>
</template>
