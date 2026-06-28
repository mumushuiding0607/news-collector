<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ArrowRight } from "@element-plus/icons-vue";
import { useMobile } from "../../composables/useMobile";
import LogViewer from "../../components/LogViewer.vue";
import TaskDialog from "./TaskDialog.vue";
import { useScheduleTasks, handlerLogMap } from "./useScheduleTasks";

const { isMobile } = useMobile();
const { tasks, loading, fetchTasks, saveTask, deleteTask, triggerTask } = useScheduleTasks();

const dialogVisible = ref(false);
const dialogTitle = ref("新增任务");
const isEditing = ref(false);
const dialogInitial = ref<Record<string, unknown>>({});

const logVisible = ref(false);
const logTitle = ref("任务日志");
const logFile = ref("");

function openAdd() {
  dialogTitle.value = "新增任务";
  isEditing.value = false;
  dialogInitial.value = { id: "", name: "", description: "", cron: "", enabled: true, handler: "" };
  dialogVisible.value = true;
}

function openEdit(task: Record<string, unknown>) {
  dialogTitle.value = "修改任务";
  isEditing.value = true;
  dialogInitial.value = { ...task };
  dialogVisible.value = true;
}

async function onSave(task: Record<string, unknown>, isEdit: boolean, currentId: string) {
  try {
    await saveTask(task, isEdit, currentId);
    dialogVisible.value = false;
  } catch (e) {
    console.error(e);
    alert("保存失败");
  }
}

async function onDelete(taskId: string) {
  if (!confirm(`确定删除任务 ${taskId} 吗？`)) return;
  try {
    await deleteTask(taskId);
  } catch (e) {
    console.error(e);
    alert("删除失败");
  }
}

async function onTrigger(task: Record<string, unknown>) {
  if (!confirm(`确定手动触发任务 ${task.name} 吗？`)) return;
  try {
    await triggerTask(task.id as string);
    logTitle.value = `任务日志 - ${task.name}`;
    logFile.value = handlerLogMap[task.handler as string] || "";
    logVisible.value = true;
  } catch (e) {
    console.error(e);
    alert("触发失败");
  }
}

onMounted(fetchTasks);
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2 style="color: var(--text-h); margin: 0">定时任务</h2>
      <el-button type="primary" @click="openAdd">新增任务</el-button>
    </div>

    <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
      <div v-if="!isMobile" :style="{ overflowX: 'auto' }">
        <el-table :data="tasks" v-loading="loading" stripe style="color: var(--text); min-width: 800px">
          <el-table-column prop="id" label="任务ID" width="150" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
          <el-table-column prop="cron" label="Cron" width="150">
            <template #default="{ row }">
              <code style="color: var(--success)">{{ row.cron }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="handler" label="处理器" width="250" show-overflow-tooltip />
          <el-table-column prop="enabled" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? "启用" : "停用" }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="success" link @click="onTrigger(row)">触发</el-button>
              <el-button size="small" type="danger" link @click="onDelete(row.id as string)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-else v-loading="loading">
        <div v-if="tasks.length === 0" style="color: var(--text-muted); text-align: center; padding: 40px">暂无定时任务</div>
        <div
          v-for="row in tasks"
          :key="row.id as string"
          style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px"
        >
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
            <div style="flex: 1; cursor: pointer" @click="openEdit(row)">
              <div style="display: flex; align-items: center; margin-bottom: 4px">
                <span style="color: var(--primary); font-size: 14px; font-weight: 500">{{ row.name }}</span>
                <el-icon style="color: var(--primary); margin-left: 4px"><ArrowRight /></el-icon>
              </div>
              <code style="color: var(--success); font-size: 12px">{{ row.cron }}</code>
            </div>
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? "启用" : "停用" }}</el-tag>
          </div>
          <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 10px; word-break: break-all">{{ row.description }}</div>
          <div style="color: var(--text-muted); font-size: 11px; margin-bottom: 10px; word-break: break-all">{{ row.handler }}</div>
          <div style="display: flex; gap: 8px">
            <el-button size="small" type="primary" style="flex: 1" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="success" style="flex: 1" @click="onTrigger(row)">触发</el-button>
            <el-button size="small" type="danger" style="flex: 1" @click="onDelete(row.id as string)">删除</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <TaskDialog
      v-model:visible="dialogVisible"
      :title="dialogTitle"
      :is-edit="isEditing"
      :initial="dialogInitial"
      @save="onSave"
    />

    <LogViewer v-model:visible="logVisible" :log-file="logFile" :title="logTitle" />
  </div>
</template>
