import { ref } from "vue";
import { getScheduleTasks, createScheduleTask, updateScheduleTask, deleteScheduleTask, triggerScheduleTask } from "../../api";

// handler → 日志文件 映射（trigger 后展示对应日志）
export const handlerLogMap: Record<string, string> = {
  "script.crawl.crawler.main": "list_crawler.log",
  "backend.service.news_pipeline.run_pipeline": "pipeline.log",
};

export const handlerOptions = [
  { value: "backend.service.news_pipeline.run_pipeline", label: "新闻采集管道" },
  { value: "script.crawl.crawler.main", label: "爬虫主程序" },
];

export function useScheduleTasks() {
  const tasks = ref<Record<string, unknown>[]>([]);
  const loading = ref(false);

  async function fetchTasks() {
    loading.value = true;
    try {
      const res = (await getScheduleTasks()) as { tasks?: Record<string, unknown>[] };
      tasks.value = res.tasks || [];
    } catch (e) {
      console.error(e);
    } finally {
      loading.value = false;
    }
  }

  async function saveTask(task: Record<string, unknown>, isEdit: boolean, currentId: string) {
    if (isEdit) {
      await updateScheduleTask(currentId, task);
    } else {
      await createScheduleTask(task);
    }
    await fetchTasks();
  }

  async function deleteTask(taskId: string) {
    await deleteScheduleTask(taskId);
    await fetchTasks();
  }

  async function triggerTask(taskId: string) {
    await triggerScheduleTask(taskId);
  }

  return { tasks, loading, fetchTasks, saveTask, deleteTask, triggerTask };
}
