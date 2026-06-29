import axios from "axios";
import { ElMessage } from "element-plus";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:31234",
  timeout: 10000,
});

// 请求拦截器：注入 token
api.interceptors.request.use(async (config) => {
  const token = localStorage.getItem("admin_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error.response?.data?.detail;
    const msg = detail || error.message;
    if (detail) {
      ElMessage.error(msg);
    } else {
      console.error("API Error:", msg);
    }
    return Promise.reject(msg);
  }
);

export default api;
