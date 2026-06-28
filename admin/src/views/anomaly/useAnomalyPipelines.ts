import { ElMessageBox } from "element-plus";
import {
  runAnomalyNewsPipelineStep,
  runAnomalyNewsPipeline,
  runAnomalySourcePipelineStep,
} from "../../api";
import { newsPipelineSteps, sourcePipelineSteps } from "./pipelineConfig";

export function useAnomalyPipelines(emit: (e: "open-log", title: string, file: string) => void) {
  function openLog(title: string, file: string) {
    emit("open-log", title, file);
  }

  async function runNewsStep(step: number, desc: string) {
    try {
      await ElMessageBox.confirm(`确认执行「${desc}」？`, "确认执行", { type: "info" });
    } catch {
      return;
    }
    const cfg = newsPipelineSteps.find((s) => s.step === step);
    openLog(`消息流水线 - ${desc}`, `${cfg?.logFile}.log`);
    try {
      await runAnomalyNewsPipelineStep(step);
    } catch {
      // interceptor shows popup
    }
  }

  async function runNewsFull() {
    try {
      await ElMessageBox.confirm("确认执行消息流水线（采集→确认数据源→抓正文→生成简报）？", "确认执行", { type: "info" });
    } catch {
      return;
    }
    openLog("消息流水线", "anomaly_fetcher.log");
    try {
      await runAnomalyNewsPipeline();
    } catch {
      // interceptor shows popup
    }
  }

  async function runSourceStep(step: number, desc: string) {
    try {
      await ElMessageBox.confirm(`确认执行「${desc}」？`, "确认执行", { type: "info" });
    } catch {
      return;
    }
    const cfg = sourcePipelineSteps.find((s) => s.step === step);
    openLog(`数据源步骤 - ${desc}`, `${cfg?.logFile}.log`);
    try {
      await runAnomalySourcePipelineStep(step);
    } catch {
      // interceptor shows popup
    }
  }

  return { runNewsStep, runNewsFull, runSourceStep };
}
