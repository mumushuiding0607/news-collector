<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useUserStore } from "../stores/user";
import { useNewsTypeStore } from "../stores/newsType";
import { getSidebarMenu } from "../api/modules/config";
import { useMobile } from "../composables/useMobile";
import { Menu, ArrowDown, ArrowRight } from "@element-plus/icons-vue";

const { isMobile } = useMobile();

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const newsTypeStore = useNewsTypeStore();
const drawerVisible = ref(false);

// 侧边栏菜单配置
const sidebarConfig = ref<{
  default: string;
  newsTypes: Record<string, {
    label: string;
    icon: string;
    modules: { path: string; label: string; icon: string }[];
  }>;
}>({ default: "stock", newsTypes: {} });

// 所有新闻类型列表
const newsTypeList = computed(() => {
  return Object.entries(sidebarConfig.value.newsTypes).map(([key, val]) => ({
    key,
    label: val.label,
    icon: val.icon,
  }));
});

function handleLogout() {
  userStore.logout();
  router.push("/login");
}

function navigateTo(path: string) {
  router.push(path);
  if (isMobile.value) {
    drawerVisible.value = false;
  }
}

// 点击新闻类型头部：切换选中类型
function selectNewsType(type: string) {
  newsTypeStore.setNewsType(type as "stock" | "ai");
}

function isActive(path: string) {
  return route.path === path;
}

// 自动关闭抽屉
watch(isMobile, (mobile) => {
  if (!mobile) {
    drawerVisible.value = false;
  }
});

onMounted(async () => {
  try {
    const data = await getSidebarMenu() as typeof sidebarConfig.value;
    sidebarConfig.value = data;
    if (data.default && data.default !== newsTypeStore.newsType) {
      newsTypeStore.setNewsType(data.default as "stock" | "ai");
    }
  } catch (e) {
    console.error("Failed to load sidebar config:", e);
    sidebarConfig.value = {
      default: "stock",
      newsTypes: {
        stock: {
          label: "股市新闻",
          icon: "TrendingUp",
          modules: [
            { path: "/dashboard", label: "控制台", icon: "Monitor" },
            { path: "/news", label: "新闻管理", icon: "Document" },
            { path: "/anomaly", label: "异动消息", icon: "Lightning" },
            { path: "/users", label: "用户管理", icon: "User" },
            { path: "/subscriptions", label: "订阅管理", icon: "Tickets" },
            { path: "/comments", label: "评论管理", icon: "ChatLineSquare" },
            { path: "/sources", label: "数据源配置管理", icon: "Link" },
            { path: "/config", label: "后台配置", icon: "Tools" },
            { path: "/schedule", label: "定时任务", icon: "Timer" },
            { path: "/logs", label: "日志管理", icon: "DocumentCopy" },
          ],
        },
        ai: {
          label: "AI新闻",
          icon: "Cpu",
          modules: [
            { path: "/news", label: "新闻管理", icon: "Document" },
            { path: "/sources", label: "数据源配置管理", icon: "Link" },
          ],
        },
      },
    };
  }
});
</script>

<template>
  <el-container style="height: 100vh">
    <!-- 移动端侧边栏 -->
    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      direction="ltr"
      size="200px"
      :show-close="false"
      :with-header="false"
    >
      <div style="padding: 12px 16px; color: var(--text-h); font-size: 14px; font-weight: bold; border-bottom: 1px solid var(--border)">
        新闻指南针 · Admin
      </div>
      <div style="padding: 8px 0">
        <!-- 新闻类型选择器 -->
        <div
          v-for="nt in newsTypeList"
          :key="nt.key"
        >
          <!-- 类型头部：始终显示 -->
          <div
            @click="selectNewsType(nt.key)"
            style="display: flex; align-items: center; gap: 8px; padding: 10px 16px; cursor: pointer; font-size: 14px; font-weight: 600; color: var(--text)"
          >
            <el-icon size="14" style="color: var(--text-muted)">
              <ArrowDown v-if="newsTypeStore.newsType === nt.key" />
              <ArrowRight v-else />
            </el-icon>
            <span>{{ nt.label }}</span>
          </div>
          <!-- 子菜单：当前选中的类型才显示 -->
          <div v-show="newsTypeStore.newsType === nt.key" style="padding-left: 28px">
            <div
              v-for="item in sidebarConfig.newsTypes[nt.key]?.modules"
              :key="item.path"
              @click="navigateTo(item.path)"
              :style="{
                padding: '10px 12px',
                cursor: 'pointer',
                borderRadius: '8px',
                background: isActive(item.path) ? 'rgba(147, 51, 234, 0.15)' : 'transparent',
                color: isActive(item.path) ? '#9333ea' : 'var(--text)',
                fontSize: '13px',
                fontWeight: isActive(item.path) ? 600 : 400,
                marginBottom: '2px',
                transition: 'all 0.2s'
              }"
            >
              {{ item.label }}
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 桌面端侧边栏 -->
    <el-aside v-if="!isMobile" style="width: 200px; background: var(--sidebar-bg); border-right: 1px solid var(--border)">
      <div style="padding: 12px 16px; color: var(--text-h); font-size: 14px; font-weight: bold; border-bottom: 1px solid var(--border)">
        新闻指南针 · Admin
      </div>
      <div style="padding: 8px 0">
        <!-- 新闻类型选择器 -->
        <div
          v-for="nt in newsTypeList"
          :key="nt.key"
        >
          <!-- 类型头部：始终显示 -->
          <div
            @click="selectNewsType(nt.key)"
            style="display: flex; align-items: center; gap: 8px; padding: 10px 16px; cursor: pointer; font-size: 14px; font-weight: 600; color: var(--text)"
          >
            <el-icon size="14" style="color: var(--text-muted)">
              <ArrowDown v-if="newsTypeStore.newsType === nt.key" />
              <ArrowRight v-else />
            </el-icon>
            <span>{{ nt.label }}</span>
          </div>
          <!-- 子菜单：当前选中的类型才显示 -->
          <div v-show="newsTypeStore.newsType === nt.key" style="padding-left: 28px">
            <div
              v-for="item in sidebarConfig.newsTypes[nt.key]?.modules"
              :key="item.path"
              @click="navigateTo(item.path)"
              :style="{
                padding: '10px 12px',
                cursor: 'pointer',
                borderRadius: '8px',
                background: isActive(item.path) ? 'rgba(147, 51, 234, 0.15)' : 'transparent',
                color: isActive(item.path) ? '#9333ea' : 'var(--text)',
                fontSize: '13px',
                fontWeight: isActive(item.path) ? 600 : 400,
                marginBottom: '2px',
                transition: 'all 0.2s'
              }"
            >
              {{ item.label }}
            </div>
          </div>
        </div>
      </div>
    </el-aside>

    <el-container>
      <el-header style="background: var(--sidebar-bg); display: flex; align-items: center; padding: 0 16px; border-bottom: 1px solid var(--border); height: 56px;">
        <!-- 移动端菜单按钮 -->
        <el-button
          v-if="isMobile"
          text
          @click="drawerVisible = true"
          style="color: var(--text)"
        >
          <el-icon size="20"><Menu /></el-icon>
        </el-button>

        <!-- 桌面端保留退出按钮靠右 -->
        <div style="flex: 1; display: flex; justify-content: flex-end;">
          <el-button text @click="handleLogout" style="color: var(--text)">
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main style="background: var(--bg); padding: 16px;">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
