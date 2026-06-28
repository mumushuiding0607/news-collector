import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/login/index.vue"),
  },
  {
    path: "/",
    component: () => import("../layout/index.vue"),
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("../views/dashboard/index.vue"),
      },
      {
        path: "news",
        name: "News",
        component: () => import("../views/news/index.vue"),
      },
      {
        path: "anomaly",
        name: "Anomaly",
        component: () => import("../views/anomaly/index.vue"),
      },
      {
        path: "users",
        name: "Users",
        component: () => import("../views/user/index.vue"),
      },
      {
        path: "subscriptions",
        name: "Subscriptions",
        component: () => import("../views/subscription/index.vue"),
      },
      {
        path: "comments",
        name: "Comments",
        component: () => import("../views/comment/index.vue"),
      },
      {
        path: "config",
        name: "Config",
        component: () => import("../views/config/index.vue"),
      },
      {
        path: "schedule",
        name: "Schedule",
        component: () => import("../views/schedule/index.vue"),
      },
      {
        path: "logs",
        name: "Logs",
        component: () => import("../views/logs/index.vue"),
      },
      {
        path: "sources",
        name: "Sources",
        component: () => import("../views/sources/index.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("admin_token");
  if (!token && to.path !== "/login") {
    next("/login");
  } else {
    next();
  }
});

export default router;