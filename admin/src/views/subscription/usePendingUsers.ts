import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getPendingSubscriptions, confirmSubscription, rejectSubscription } from "../../api";

export function usePendingUsers() {
  const loading = ref(false);
  const list = ref<Record<string, unknown>[]>([]);

  async function fetchData() {
    loading.value = true;
    try {
      const res = (await getPendingSubscriptions()) as { list?: Record<string, unknown>[] };
      list.value = res.list || [];
    } catch (e) {
      console.error(e);
    } finally {
      loading.value = false;
    }
  }

  async function handleConfirm(userId: number) {
    await confirmSubscription(userId);
    ElMessage.success("已确认订阅");
    await fetchData();
  }

  async function handleReject(userId: number) {
    try {
      await ElMessageBox.confirm("将发送邮件通知用户上传付款凭证，是否继续？", "确认撤销", { type: "warning" });
    } catch {
      return;
    }
    await rejectSubscription(userId);
    ElMessage.success("已发送提醒邮件");
    await fetchData();
  }

  return { loading, list, fetchData, handleConfirm, handleReject };
}
