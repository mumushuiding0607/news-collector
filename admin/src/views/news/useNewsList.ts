import { ref, watch } from "vue";
import { getNewsList, getPrimarySourcesList, getAiAllNews, markUseful } from "../../api";
import { useNewsTypeStore } from "../../stores/newsType";
import type { TabType } from "./types";

export function useNewsList() {
  const newsTypeStore = useNewsTypeStore();
  const loading = ref(false);
  const tableData = ref<Record<string, unknown>[]>([]);
  const pagination = ref({ page: 1, limit: 20, total: 0 });
  const filterForm = ref({ status: "", source_name: "" });

  async function fetchList(tab: TabType) {
    loading.value = true;
    try {
      // AI 新闻：使用 getAiAllNews
      if (newsTypeStore.newsType === "ai") {
        const res = (await getAiAllNews()) as {
          latest?: { data?: Record<string, unknown>[]; count?: number };
          history?: { data?: Record<string, unknown>[]; count?: number };
        };
        const latestData = res.latest?.data || [];
        const historyData = res.history?.data || [];
        const combined = [...latestData, ...historyData];
        // 转换为与股市新闻相同的字段名
        tableData.value = combined.map((item: Record<string, unknown>) => ({
          id: item.id,
          title: item.title,
          url: item.url,
          source_name: item.sourceName,
          publish_time: item.publishTime,
          summary: item.summary || item.highlights || "",
          importance_score: item.score,
          reason: item.reason,
          content_length: item.content ? String(item.content).length : 0,
          status: "scored",
          is_useful: null,
        }));
        pagination.value.total = (res.latest?.count || 0) + (res.history?.count || 0);
        return;
      }

      // 股市新闻
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

  // 新闻类型切换时重新加载
  watch(() => newsTypeStore.newsType, () => {
    pagination.value.page = 1;
  });

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
