<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getComments, getFeedbackSummary } from "../../api";
import NewsDetail from "../../components/NewsDetail.vue";
import CommentTable from "./CommentTable.vue";

const activeTab = ref("comments");
const commentsData = ref<Record<string, unknown>[]>([]);
const feedbackData = ref<Record<string, unknown>[]>([]);
const loading = ref(false);
const pagination = ref({ page: 1, limit: 20, total: 0 });

const detailVisible = ref(false);
const detailNewsId = ref<number | null>(null);

async function fetchComments() {
  loading.value = true;
  try {
    const res = (await getComments({ page: pagination.value.page, limit: pagination.value.limit })) as {
      list?: Record<string, unknown>[]; total?: number;
    };
    commentsData.value = res.list || [];
    pagination.value.total = res.total || 0;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function fetchFeedbackSummary() {
  loading.value = true;
  try {
    const res = (await getFeedbackSummary({ page: pagination.value.page, limit: pagination.value.limit })) as {
      list?: Record<string, unknown>[]; total?: number;
    };
    feedbackData.value = res.list || [];
    pagination.value.total = res.total || 0;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function onTabChange(tab: string) {
  activeTab.value = tab;
  pagination.value.page = 1;
  if (tab === "comments") fetchComments();
  else fetchFeedbackSummary();
}

function openNews(newsId: number) {
  detailNewsId.value = newsId;
  detailVisible.value = true;
}

onMounted(fetchComments);
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">评论管理</h2>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="评论列表" name="comments">
        <CommentTable
          :data="commentsData"
          :loading="loading"
          mode="comments"
          :page="pagination.page"
          :limit="pagination.limit"
          :total="pagination.total"
          @open-news="openNews"
          @page-change="(p: number) => { pagination.page = p; fetchComments() }"
        />
      </el-tab-pane>
      <el-tab-pane label="评论汇总" name="summary">
        <CommentTable
          :data="feedbackData"
          :loading="loading"
          mode="feedback"
          :page="pagination.page"
          :limit="pagination.limit"
          :total="pagination.total"
          @open-news="openNews"
          @page-change="(p: number) => { pagination.page = p; fetchFeedbackSummary() }"
        />
      </el-tab-pane>
    </el-tabs>

    <NewsDetail v-model:visible="detailVisible" :news-id="detailNewsId" />
  </div>
</template>
