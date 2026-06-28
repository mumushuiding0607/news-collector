import { ref } from "vue";
import { getAnomalyNewsList, deleteAnomalyNews, markAnomalyProcessed, markAllAnomalyProcessed } from "../../api";
import { ElMessage, ElMessageBox } from "element-plus";

export function useAnomalyList() {
  const loading = ref(false);
  const tableData = ref<Record<string, unknown>[]>([]);
  const pagination = ref({ page: 1, limit: 20, total: 0 });
  const filterForm = ref({ source_name: "", title: "", processed: "" as "" | "0" | "1" });

  async function fetchData() {
    loading.value = true;
    try {
      const params: Record<string, unknown> = {
        page: pagination.value.page,
        limit: pagination.value.limit,
      };
      if (filterForm.value.source_name) params.source_name = filterForm.value.source_name;
      if (filterForm.value.title) params.title = filterForm.value.title;
      if (filterForm.value.processed !== "") params.processed = parseInt(filterForm.value.processed);
      const res = (await getAnomalyNewsList(params)) as { list?: Record<string, unknown>[]; total?: number };
      tableData.value = res.list || [];
      pagination.value.total = res.total || 0;
    } catch (e) {
      console.error(e);
    } finally {
      loading.value = false;
    }
  }

  async function handleDelete(id: number) {
    try {
      await ElMessageBox.confirm("确认删除该异动消息？", "删除确认", { type: "warning" });
      await deleteAnomalyNews(id);
      ElMessage.success("删除成功");
      await fetchData();
    } catch {
      // user cancel or error
    }
  }

  async function handleMarkProcessed(id: number) {
    await markAnomalyProcessed(id);
    ElMessage.success("已标记为处理");
    await fetchData();
  }

  async function handleMarkAllProcessed() {
    try {
      await ElMessageBox.confirm("确认标记所有异动消息为已处理？", "确认操作", { type: "warning" });
      const res = (await markAllAnomalyProcessed()) as { marked?: number };
      ElMessage.success(`已标记 ${res.marked || 0} 条为已处理`);
      await fetchData();
    } catch {
      // user cancel or error
    }
  }

  function handleSearch() {
    pagination.value.page = 1;
    fetchData();
  }

  function handleReset() {
    filterForm.value = { source_name: "", title: "", processed: "" };
    pagination.value.page = 1;
    fetchData();
  }

  function handlePageChange(page: number) {
    pagination.value.page = page;
    fetchData();
  }

  return {
    loading,
    tableData,
    pagination,
    filterForm,
    fetchData,
    handleDelete,
    handleMarkProcessed,
    handleMarkAllProcessed,
    handleSearch,
    handleReset,
    handlePageChange,
  };
}
