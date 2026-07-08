import { defineStore } from "pinia";
import { ref } from "vue";

export type NewsType = "stock" | "ai";

export const useNewsTypeStore = defineStore("newsType", () => {
  const newsType = ref<NewsType>((localStorage.getItem("newsType") as NewsType) || "stock");

  function setNewsType(type: NewsType) {
    newsType.value = type;
    localStorage.setItem("newsType", type);
  }

  return { newsType, setNewsType };
});
