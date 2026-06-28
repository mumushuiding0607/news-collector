<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "../stores/user";
import { Menu } from "@element-plus/icons-vue";
import { useMobile } from "../composables/useMobile";

const { isMobile } = useMobile();

const router = useRouter();
const userStore = useUserStore();
const drawerVisible = ref(false);

const menu = [
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
];

function handleLogout() {
  userStore.logout();
  router.push("/login");
}

// Auto-close drawer when switching to desktop
watch(isMobile, (mobile) => {
  if (!mobile) {
    drawerVisible.value = false;
  }
});

const asideStyle = computed(() => {
  if (isMobile.value) return {};
  return { width: "180px" };
});

function navigateTo(path: string) {
  router.push(path);
  if (isMobile.value) {
    drawerVisible.value = false;
  }
}
</script>

<template>
  <el-container style="height: 100vh">
    <!-- 移动端侧边栏 -->
    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      direction="ltr"
      size="180px"
      :show-close="false"
      :with-header="false"
    >
      <div style="padding: 12px 16px; color: var(--text-h); font-size: 14px; font-weight: bold; border-bottom: 1px solid var(--border)">
        新闻风向标 · Admin
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="var(--sidebar-bg)"
        text-color="var(--text)"
        active-text-color="var(--gold)"
        :ellipsis="false"
        @select="navigateTo"
      >
        <el-menu-item v-for="item in menu" :key="item.path" :index="item.path">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
    </el-drawer>

    <!-- 桌面端侧边栏 -->
    <el-aside v-if="!isMobile" :style="asideStyle" style="background: var(--sidebar-bg); border-right: 1px solid var(--border)">
      <div style="padding: 12px 16px; color: var(--text-h); font-size: 14px; font-weight: bold; border-bottom: 1px solid var(--border)">
        新闻风向标 · Admin
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="var(--sidebar-bg)"
        text-color="var(--text)"
        active-text-color="var(--gold)"
        :ellipsis="false"
      >
        <el-menu-item v-for="item in menu" :key="item.path" :index="item.path">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
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