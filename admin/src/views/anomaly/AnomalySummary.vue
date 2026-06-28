<script setup lang="ts">
// 异动简报列表：复用通用 SummaryListView，通过 actions 插槽注入流水线步骤下拉
import { MoreFilled } from "@element-plus/icons-vue";
import SummaryListView from "../../components/SummaryListView.vue";
import { useAnomalyPipelines } from "./useAnomalyPipelines";
import { newsPipelineSteps, sourcePipelineSteps } from "./pipelineConfig";

const emit = defineEmits<{
  (e: "open-log", title: string, file: string): void;
}>();
const pipelines = useAnomalyPipelines(emit);
</script>

<template>
  <SummaryListView type="异动简报">
    <template #actions>
      <el-dropdown trigger="click" @command="(cmd: number) => { if (cmd === 0) { pipelines.runNewsFull() } else { const s = newsPipelineSteps.find(p => p.step === cmd); if (s) pipelines.runNewsStep(s.step, s.desc) } }">
        <el-button type="success" size="small">
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
        <el-button type="warning" size="small">
          数据源步骤 <el-icon class="el-icon--right"><MoreFilled /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-for="s in sourcePipelineSteps" :key="s.step" :command="s.step">Step {{ s.step }} - {{ s.desc }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </template>
  </SummaryListView>
</template>
