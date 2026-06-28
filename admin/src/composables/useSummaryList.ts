import { ref } from "vue";
import { getSummaries, getSummaryByDate } from "../api";

// 通用简报列表：新闻简报 / 异动简报 共用，仅 type 不同
export function useSummaryList(type: string) {
  const loading = ref(false);
  const list = ref<Record<string, unknown>[]>([]);
  const pagination = ref({ page: 1, limit: 20, total: 0 });
  const detail = ref<Record<string, unknown>>({});
  const detailVisible = ref(false);

  async function fetchList() {
    loading.value = true;
    try {
      const res = (await getSummaries({ type, page: pagination.value.page, limit: pagination.value.limit })) as {
        items?: Record<string, unknown>[];
        total?: number;
      };
      list.value = res.items || [];
      pagination.value.total = res.total || 0;
    } catch (e) {
      console.error(e);
    } finally {
      loading.value = false;
    }
  }

  async function openDetail(date: string) {
    const res = (await getSummaryByDate(date, type)) as Record<string, unknown>;
    detail.value = res || {};
    detailVisible.value = true;
  }

  function onPageChange(page: number) {
    pagination.value.page = page;
    fetchList();
  }

  return { loading, list, pagination, detail, detailVisible, fetchList, openDetail, onPageChange };
}
