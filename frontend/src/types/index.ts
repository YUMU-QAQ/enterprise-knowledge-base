/** 全局类型定义 */

export interface User {
  id: number;
  username: string;
  email: string | null;
  display_name: string;
  avatar_url: string | null;
  source: string;
  is_super_admin: boolean;
  created_at: string;
}

export interface DocumentItem {
  id: number;
  title: string;
  summary_text: string | null;
  format: string;
  status: string;
  view_count: number;
  like_count: number;
  category_id: number | null;
  category_name: string | null;
  created_by: number;
  author_name: string | null;
  tags: TagInfo[];
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentItem {
  content: string | null;
  content_md: string | null;
}

export interface TagInfo {
  id: number;
  name: string;
  color?: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  parent_id: number | null;
  sort_order: number;
  children: Category[];
  document_count: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface APIResponse<T = any> {
  code: number;
  message: string;
  data: T;
  pagination?: PaginationMeta;
}

export interface SearchResult {
  id: number;
  title: string;
  summary_text: string;
  category_id: number | null;
  category_name: string | null;
  author_name: string | null;
  tags: string[];
  view_count: number;
  created_at: string;
  updated_at: string;
  highlight?: Record<string, string[]>;
  score: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { id: number; title: string; score: number; snippet?: string }[];
  timestamp: string;
}
