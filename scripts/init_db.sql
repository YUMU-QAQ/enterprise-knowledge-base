-- 企业知识库 — 数据库初始化脚本
-- 由 PostgreSQL 容器首次启动时自动执行

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 启用 UUID 支持
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建中文全文检索配置（可选，轻量搜索不需 ES 时使用）
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS zh (PARSER = default);
ALTER TEXT SEARCH CONFIGURATION zh
    ALTER MAPPING FOR a, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z
    WITH simple;
