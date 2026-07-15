/** API 端点定义 */

import api from "./api";

// ── 认证 ──
export const authAPI = {
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  register: (data: { username: string; password: string; email?: string; display_name: string }) =>
    api.post("/auth/register", data),
  refresh: (refresh_token: string) =>
    api.post("/auth/refresh", null, { params: { refresh_token } }),
  me: () => api.get("/auth/me"),
  feishuLoginUrl: () => api.get("/auth/feishu/login-url"),
  dingtalkLoginUrl: () => api.get("/auth/dingtalk/login-url"),
};

// ── 文档 ──
export const documentsAPI = {
  list: (params?: Record<string, any>) => api.get("/documents", { params }),
  get: (id: number) => api.get(`/documents/${id}`),
  create: (data: any) => api.post("/documents", data),
  update: (id: number, data: any) => api.put(`/documents/${id}`, data),
  delete: (id: number) => api.delete(`/documents/${id}`),
  versions: (id: number) => api.get(`/documents/${id}/versions`),
  comments: (id: number, params?: any) => api.get(`/documents/${id}/comments`, { params }),
  addComment: (id: number, content: string, parent_id?: number) =>
    api.post(`/documents/${id}/comments`, null, { params: { content, parent_id } }),
};

// ── 搜索 ──
export const searchAPI = {
  search: (params: Record<string, any>) => api.get("/search", { params }),
  suggest: (q: string) => api.get("/search/suggest", { params: { q } }),
};

// ── AI 对话 ──
export const chatAPI = {
  ask: (question: string, session_id?: string, top_k?: number) => {
    // SSE 流式调用，不使用 axios
    const token = localStorage.getItem("token");
    return fetch("/api/v1/chat/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ question, session_id, top_k }),
    });
  },
  history: (params?: any) => api.get("/chat/history", { params }),
};

// ── 摘要 ──
export const summarizeAPI = {
  generate: (document_id: number) => api.post(`/summarize/${document_id}`),
};

// ── 推荐 ──
export const recommendAPI = {
  personal: (top_k?: number) => api.get("/recommend", { params: { top_k } }),
  hot: (top_k?: number) => api.get("/recommend/hot", { params: { top_k } }),
  similar: (document_id: number, top_k?: number) =>
    api.get(`/recommend/similar/${document_id}`, { params: { top_k } }),
};

// ── 分类 ──
export const categoriesAPI = {
  list: () => api.get("/categories"),
  create: (data: any) => api.post("/categories", data),
  update: (id: number, data: any) => api.put(`/categories/${id}`, data),
  delete: (id: number) => api.delete(`/categories/${id}`),
};

// ── 标签 ──
export const tagsAPI = {
  list: () => api.get("/tags"),
  create: (name: string, color?: string) => api.post("/tags", null, { params: { name, color } }),
};

// ── 管理 ──
export const adminAPI = {
  integrations: () => api.get("/admin/integrations"),
  updateFeishu: (data: any) => api.put("/admin/integrations/feishu", data),
  updateDingtalk: (data: any) => api.put("/admin/integrations/dingtalk", data),
  syncFeishuContacts: () => api.post("/admin/integrations/feishu/sync-contacts"),
  syncDingtalkContacts: () => api.post("/admin/integrations/dingtalk/sync-contacts"),
  importFeishuDocs: (folder_token?: string) =>
    api.post("/admin/integrations/feishu/import-docs", null, { params: { folder_token } }),
  importDingtalkDocs: (folder_id?: string) =>
    api.post("/admin/integrations/dingtalk/import-docs", null, { params: { folder_id } }),
};

// ── 统计 ──
export const statsAPI = {
  overview: () => api.get("/stats/overview"),
  documents: () => api.get("/stats/documents"),
  users: () => api.get("/stats/users"),
};
