import { ref } from "vue";
import { getNewsList, getPrimarySourcesList, markUseful } from "../../api";
import type { TabType } from "./types";

export function useNewsList() {
  const loading = ref(false);
  const tableData = ref<Record<string, unknown>[]>([]);
  const pagination = ref({ page: 1, limit: 20, total: 0 });
  const filterForm = ref({ status: "", source_name: "" });

  async function fetchList(tab: TabType) {
    loading.value = true;
    try {
      const params = {
        page: pagination.value.page,
        limit: pagination.value.limit,
        status: filterForm.value.status || undefined,
        source_name: filterForm.value.source_name || undefined,
      };
      const fetcher = tab === "importance" ? getNewsList : getPrimarySourcesList;
      const res = (await fetcher(params)) as { list?: Record<string, unknown>[]; total?: number };
      tableData.value = res.list || [];
      pagination.value.total = res.total || 0;
    } catch (e) {
      console.error(e);
    } finally {
      loading.value = false;
    }
  }

  async function markUsefulFn(id: number, useful: boolean) {
    await markUseful(id, useful);
  }

  function handleSearch() {
    pagination.value.page = 1;
  }

  function handleReset() {
    filterForm.value = { status: "", source_name: "" };
    pagination.value.page = 1;
  }

  return {
    loading,
    tableData,
    pagination,
    filterForm,
    fetchList,
    markUseful: markUsefulFn,
    handleSearch,
    handleReset,
  };
}
