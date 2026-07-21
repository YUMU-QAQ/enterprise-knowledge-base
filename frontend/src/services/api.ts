/** API 客户端 — axios 封装 */

import axios from "axios";
import { useAuthStore } from "../stores/authStore";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

// 请求拦截器：自动附加 Token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (response) => {
    const data = response.data;
    if (data.code !== 0) {
      return Promise.reject(data);
    }
    return data;
  },
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    // Normalize FastAPI HTTPException format to {code, message}
    const detail = error.response?.data?.detail;
    if (detail) {
      return Promise.reject(detail);
    }
    return Promise.reject(error.response?.data || error);
  }
);

export default api;
