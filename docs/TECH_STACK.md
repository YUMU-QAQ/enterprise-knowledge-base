# 企业知识库 — 技术方案设计

> 版本: v1.0 | 日期: 2026-07-14 | 状态: 待确认

---

## 1. 项目概述

### 1.1 项目定位

面向企业内部的智能知识管理平台。支持文档协同、**语义搜索（RAG）**、**智能摘要**、**个性化推荐**，同时预置飞书/钉钉接口，实现单点登录、Bot 消息推送及文档互通。

### 1.2 规模与核心目标

| 指标 | 预期 |
|---|---|
| 日活用户 | ≤ 100 人 |
| 峰值 QPS | ~50 |
| 文档总量 | 1万-10万 级别 |
| 响应时间 | 列表页 < 200ms，搜索 < 500ms |

**核心目标**：

- **智能检索**：关键词 + 语义向量混合搜索，搜得到、搜得准
- **RAG 问答**：基于知识库内容的 AI 问答，不是搜文档而是直接给答案
- **智能摘要**：长文档自动生成摘要，快速了解要点
- **智能推荐**：基于阅读历史和岗位画像的个性化文档推荐
- **知识沉淀**：分散知识 → 结构化、可检索的组织资产
- **权限可控**：部门/角色/标签三级权限
- **生态打通**：飞书/钉钉内直接搜索、查阅、接收推送

---

## 2. 技术选型总览

```
┌───────────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                            │
│  React 18 + TypeScript + Vite + Ant Design 5 + Zustand             │
│  TipTap (富文本) + ECharts (统计) + React Query (请求缓存)         │
├───────────────────────────────────────────────────────────────────┤
│                        网关层                                       │
│  Nginx (反向代理 / 静态资源)                                        │
├───────────────────────────────────────────────────────────────────┤
│                        后端层 (Backend)                             │
│  Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Celery           │
│  LangChain (RAG 编排) + OpenAI-compatible LLM 接口                  │
├───────────────────────────────────────────────────────────────────┤
│                        数据层                                       │
│  PostgreSQL 16 + pgvector (主库+向量)                               │
│  Elasticsearch 8.x (全文检索)                                       │
│  Redis 7.x (缓存/队列/Session)                                     │
│  MinIO (文件/附件存储, S3 兼容)                                    │
├───────────────────────────────────────────────────────────────────┤
│                        AI 服务层                                    │
│  Embedding Model (BGE-M3 / text2vec-large-chinese)                 │
│  LLM (OpenAI API / 本地 Qwen3 / 兼容接口)                          │
│  Reranker (BGE-Reranker-v2)                                       │
├───────────────────────────────────────────────────────────────────┤
│                        外部集成                                     │
│  飞书开放平台  │  钉钉开放平台  │  Webhook Gateway                  │
└───────────────────────────────────────────────────────────────────┘
```

### 2.1 选型明细与理由

| 组件 | 选型 | 理由 |
|---|---|---|
| **后端语言** | Python 3.12 | AI/ML 生态最强；FastAPI 异步性能足够；团队门槛低 |
| **Web 框架** | FastAPI | 异步原生、自动 Swagger、Pydantic 类型安全 |
| **ORM** | SQLAlchemy 2.0 | 异步成熟、Alembic 迁移 |
| **前端** | React + Ant Design 5 | 企业级组件库、TS 类型安全、社区最活跃 |
| **富文本** | TipTap (ProseMirror) | 插件化、Markdown 互通、协同预留 |
| **全文搜索** | Elasticsearch 8.x | IK 中文分词、高亮/聚合/同义词企业级 |
| **向量数据库** | **pgvector** (PostgreSQL 扩展) | 与主库一体、运维简单、百万级向量足够 |
| **文件存储** | MinIO | S3 兼容、私有化免费 |
| **RAG 框架** | **LangChain + LlamaIndex** | 文档切分、检索链、Prompt 模板 |
| **Embedding** | **BGE-M3** (本地部署) | 中文 SOTA、1024/768 维、支持稀疏+稠密混合 |
| **LLM** | OpenAI 兼容接口 | 可接入 GPT-4o / 本地 Qwen3 / 任意兼容服务 |
| **Reranker** | **BGE-Reranker-v2-m3** | 召回后精排，提升 RAG 准确率 |
| **异步队列** | Celery + Redis | 摘要生成、向量化、批量导入 |

### 2.2 为什么选 pgvector 而不是 Milvus/Qdrant？

| 对比 | pgvector | Milvus / Qdrant |
|---|---|---|
| 部署复杂度 | ✅ 与 PG 一体，零额外运维 | ❌ 需独立部署，资源占用高 |
| 性能（<10万向量） | ✅ 足够（IVFFlat/HNSW 索引） | 过度设计 |
| 与业务数据 JOIN | ✅ 天然支持 | ❌ 需应用层关联 |
| 适合规模 | ✅ < 百万向量 | 千万级以上 |

> **结论**：日活 100 人、文档量 1-10 万级别，pgvector 完全够用。未来数据量增长到百万级时，可平滑迁移到 Milvus。

---

## 3. 系统架构

### 3.1 逻辑架构图

```
┌──────────┐  ┌───────────┐  ┌───────────┐
│  Web 端   │  │  飞书入口  │  │  钉钉入口  │
│ (React)  │  │ (H5/小程序) │  │ (H5/小程序) │
└────┬─────┘  └─────┬─────┘  └─────┬─────┘
     │               │              │
     └───────────────┼──────────────┘
                     │
             ┌───────┴───────┐
             │   Nginx       │
             └───────┬───────┘
                     │
        ┌────────────┴────────────┐
        │                         │
  ┌─────┴──────┐          ┌──────┴──────┐
  │  API 服务   │          │  AI 服务    │
  │ (FastAPI)  │←────────→│ (FastAPI)   │
  │ 业务逻辑   │          │ RAG / 摘要  │
  │ 权限/文档  │          │ 推荐/向量化 │
  └─────┬──────┘          └──────┬──────┘
        │                        │
        │    ┌───────────────────┤
        │    │                   │
  ┌─────┼────┼───────────┬───────┼──────┐
  │     │    │  服务层    │       │      │
  │  ┌──┴────┴──┐ ┌──────┴──┐ ┌──┴───┐ │
  │  │ 文档服务  │ │ 搜索服务 │ │AI服务│ │
  │  │ 权限服务  │ │ 索引服务 │ │推荐  │ │
  │  │ 分类标签  │ │          │ │摘要  │ │
  │  └────┬─────┘ └────┬─────┘ └──┬───┘ │
  │       │            │          │      │
  │  ┌────┴────────────┴──────────┴──┐  │
  │  │      数据访问层 (Repository)   │  │
  │  └────┬────────┬──────────┬──────┘  │
  │       │        │          │         │
  └───────┼────────┼──────────┼─────────┘
          │        │          │
    ┌─────┴──┐ ┌───┴───┐ ┌───┴───────┐
    │PostgreSQL│ │Redis │ │Elasticsearch│
    │+pgvector│ │      │ │            │
    │         │ │      │ │            │
    └─────────┘ └──────┘ └────────────┘
          │
    ┌─────┴─────┐
    │   MinIO   │
    │ (文件存储) │
    └───────────┘
```

### 3.2 为什么 AI 服务独立？

- 模型加载（Embedding / Reranker / LLM）占用显存，和业务服务资源需求不同
- 可独立扩缩容：业务 API 可能需要 2 副本，AI 服务仅需 1 副本（小规模场景）
- 小规模下也能合并部署（单机 Docker Compose 无差别）

### 3.3 项目目录结构（Monorepo）

```
enterprise-knowledge-base/
├── frontend/                        # React 前端
│   ├── src/
│   │   ├── components/              # 通用组件
│   │   │   ├── ui/                  # 基础 UI（按钮/表单/表格封装）
│   │   │   ├── RichEditor/          # 富文本编辑器
│   │   │   ├── SearchBox/           # 智能搜索框
│   │   │   ├── DocCard/             # 文档卡片
│   │   │   └── AIChat/              # AI 对话面板
│   │   ├── features/                # 业务模块
│   │   │   ├── auth/                # 登录/注册
│   │   │   ├── documents/           # 文档管理
│   │   │   ├── search/              # 搜索页
│   │   │   ├── knowledge/           # 知识浏览（分类树+列表）
│   │   │   ├── recommend/           # 推荐面板
│   │   │   ├── admin/               # 后台管理
│   │   │   └── integrations/        # 飞书/钉钉配置
│   │   ├── hooks/
│   │   ├── stores/                  # Zustand
│   │   ├── services/                # API 调用
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                         # Python 主服务
│   ├── app/
│   │   ├── api/v1/                  # REST 路由
│   │   │   ├── auth.py              # 认证
│   │   │   ├── documents.py         # 文档 CRUD
│   │   │   ├── search.py            # 混合搜索
│   │   │   ├── chat.py              # RAG 对话
│   │   │   ├── recommend.py         # 智能推荐
│   │   │   ├── summarize.py         # 智能摘要
│   │   │   ├── categories.py        # 分类管理
│   │   │   ├── admin.py             # 管理接口
│   │   │   └── webhooks.py          # 飞书/钉钉回调
│   │   ├── core/
│   │   │   ├── config.py            # 全局配置
│   │   │   ├── security.py          # JWT / OAuth
│   │   │   ├── database.py          # PG 连接
│   │   │   └── dependencies.py      # FastAPI Depends
│   │   ├── models/                  # SQLAlchemy
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── category.py
│   │   │   ├── tag.py
│   │   │   ├── permission.py
│   │   │   ├── comment.py
│   │   │   └── read_history.py
│   │   ├── schemas/                 # Pydantic
│   │   ├── services/                # 业务逻辑
│   │   │   ├── document_svc.py
│   │   │   ├── search_svc.py        # 混合搜索编排
│   │   │   ├── rag_svc.py           # RAG 问答
│   │   │   ├── summarize_svc.py     # 摘要生成
│   │   │   ├── recommend_svc.py     # 推荐算法
│   │   │   ├── auth_svc.py
│   │   │   └── notification_svc.py
│   │   ├── integrations/            # 🎯 飞书/钉钉
│   │   │   ├── base.py              # 抽象基类
│   │   │   ├── feishu/
│   │   │   │   ├── client.py        # SDK 封装
│   │   │   │   ├── auth.py          # OAuth
│   │   │   │   ├── bot.py           # Bot 消息
│   │   │   │   ├── docs.py          # 文档导入
│   │   │   │   └── contacts.py      # 通讯录
│   │   │   └── dingtalk/
│   │   │       ├── client.py
│   │   │       ├── auth.py
│   │   │       ├── bot.py
│   │   │       ├── docs.py
│   │   │       └── contacts.py
│   │   ├── ai/                      # AI 相关
│   │   │   ├── embedding.py         # 向量化服务
│   │   │   ├── llm.py               # LLM 调用封装
│   │   │   ├── reranker.py          # 精排
│   │   │   ├── splitter.py          # 文档切分策略
│   │   │   └── prompts.py           # Prompt 模板
│   │   ├── tasks/                   # Celery 异步任务
│   │   │   ├── index_tasks.py       # ES 索引 + 向量化
│   │   │   ├── summarize_tasks.py   # 摘要生成
│   │   │   ├── notify_tasks.py      # 消息推送
│   │   │   └── import_tasks.py      # 批量导入
│   │   └── utils/
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── docs/
│   ├── TECH_STACK.md                # 本文件
│   ├── API.md
│   ├── INTEGRATION_FEISHU.md
│   ├── INTEGRATION_DINGTALK.md
│   └── DEPLOY.md
│
├── docker/
│   ├── docker-compose.yml           # 本地开发
│   ├── docker-compose.prod.yml      # 生产部署
│   └── nginx/nginx.conf
│
├── scripts/
│   └── init_db.sql
│
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. 核心数据模型

### 4.1 ER 图

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│     User     │       │    Document      │       │   Category   │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ id (PK)      │──┐    │ id (PK)          │──┐    │ id (PK)      │
│ username     │  │    │ title            │  │    │ name         │
│ email        │  │    │ content (text)   │  │    │ slug         │
│ display_name │  │    │ content_md       │  │    │ description  │
│ avatar_url   │  │    │ summary_text     │  │    │ parent_id    │──┐
│ source       │  │    │ summary_vector   │  │    │ icon         │  │
│ (local/feishu│  │    │ format (md/richtx│  │    │ sort_order   │  │
│  /dingtalk)  │  │    │ status (draft/   │  │    │ created_at   │  │
│ external_id  │  │    │  published/arch) │  │    └──────────────┘  │
│ is_active    │  │    │ view_count       │  │                     │
│ created_at   │  │    │ like_count       │  │                     │
│ updated_at   │  │    │ category_id (FK)─┤──┤──┐                  │
└──────────────┘  │    │ created_by (FK)──┤──┘  │                  │
                  │    │ updated_by (FK)──┤──┐  │                  │
                  │    │ created_at       │  │  │                  │
┌─────────────────┴──┐ │ updated_at       │  │  │                  │
│  ReadHistory       │ │ embedding        │  │  │                  │
│  (用户阅读记录)     │ │ (pgvector 768d)  │  │  │                  │
├────────────────────┤ └──────────────────┘  │  │                  │
│ user_id (FK)       │          │             │  │                  │
│ document_id (FK)   │  ┌───────┴──────┐      │  │                  │
│ read_count         │  │  DocVersion  │      │  │                  │
│ last_read_at       │  ├──────────────┤      │  │                  │
│ read_duration      │  │ id (PK)      │      │  │                  │
└────────────────────┘  │ document_id  │──┐   │  │                  │
                        │ version_num  │  │   │  │                  │
                        │ content      │  │   │  │                  │
                        │ change_log   │  │   │  │                  │
                        │ created_by ──┤──┘   │  │                  │
                        │ created_at   │      │  │                  │
                        └──────────────┘      │  │                  │
                                              │  │                  │
┌────────────────────┐  ┌────────────────┐    │  │                  │
│   DocumentTag      │  │   Permission   │    │  │                  │
├────────────────────┤  ├────────────────┤    │  │                  │
│ document_id (FK)   │  │ resource_type  │    │  │                  │
│ tag_id (FK)        │  │ resource_id    │    │  │                  │
└──────┬─────────────┘  │ role (reader/  │    │  │                  │
       │                 │  editor/admin)│    │  │                  │
┌──────┴─────────────┐  │ target_type    │    │  │                  │
│       Tag          │  │ target_id      │    │  │                  │
├────────────────────┤  └────────────────┘    │  │                  │
│ id (PK)            │                        │  │                  │
│ name / color       │                        │  │                  │
└────────────────────┘                        │  │                  │
                                              │  │                  │
┌─────────────────────────────────────────────┘  │                  │
│  ┌─────────────────────────────────────────────┘                  │
│  │  ┌────────────────────────────────────────────────────────────┘
│  │  │
└──┴──┴───┐
   Comment   │
   ──────────│
   id (PK)   │
   document_id│
   user_id   │
   content   │
   parent_id │──┐ (自引用)
   created_at│  │
   updated_at│  │
   ──────────│  │
      ┌──────┘  │
      └─────────┘
```

### 4.2 关键索引

| 表 | 索引 | 用途 |
|---|---|---|
| `document` | `(category_id, status, published_at DESC)` | 分类浏览 |
| `document` | `(created_by, created_at DESC)` | 我的文档 |
| `document` | `embedding` **IVFFlat/HNSW** | 语义搜索（pgvector） |
| `permission` | `(resource_type, resource_id, target_type, target_id)` UNIQUE | 权限校验 |
| `read_history` | `(user_id, document_id)` UNIQUE | 阅读去重 |
| `read_history` | `(user_id, last_read_at DESC)` | 用户最近阅读 |

---

## 5. AI 能力设计 🔥

### 5.1 整体流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        文档入库管道                               │
│                                                                  │
│  用户创建/导入文档                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │ 文档解析 │───→│ 智能分块  │───→│ 向量化   │───→│ 双写存储  │    │
│  │Markdown │    │(语义分块) │    │(BGE-M3) │    │PG+ES    │    │
│  └─────────┘    └──────────┘    └──────────┘    └──────────┘    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │ 摘要生成  │──→ 写入 document.summary_text + summary_vector    │
│  │(LLM异步) │                                                    │
│  └──────────┘                                                    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        RAG 问答流程                               │
│                                                                  │
│  用户提问                                                        │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │ 问题向量化│ (BGE-M3)                                          │
│  └────┬─────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────┐                   │
│  │           混合召回 (Top-K)                │                   │
│  │  ┌────────────┐  ┌────────────────────┐  │                   │
│  │  │ pgvector   │  │ Elasticsearch      │  │                   │
│  │  │ 语义相似度  │  │ BM25+IK 关键词匹配  │  │                   │
│  │  └─────┬──────┘  └────────┬───────────┘  │                   │
│  │        │                  │              │                   │
│  │        └────────┬─────────┘              │                   │
│  │                 ▼                        │                   │
│  │         ┌──────────────┐                │                   │
│  │         │ RRF 融合排序  │                │                   │
│  │         └──────┬───────┘                │                   │
│  └────────────────┼────────────────────────┘                   │
│                   │                                              │
│                   ▼                                              │
│  ┌──────────────────────────────┐                               │
│  │        Reranker 精排         │                               │
│  │    (BGE-Reranker-v2-m3)     │                               │
│  │  召回 Top-20 → 精排 Top-5   │                               │
│  └──────────────┬───────────────┘                               │
│                   │                                              │
│                   ▼                                              │
│  ┌──────────────────────────────┐                               │
│  │  提示词构建 + LLM 生成回答    │                               │
│  │  系统Prompt + Top-5片段      │                               │
│  │  + 对话历史 + 用户问题       │                               │
│  └──────────────┬───────────────┘                               │
│                   │                                              │
│                   ▼                                              │
│  流式返回答案 + 引用来源                                         │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 智能摘要

```
触发时机：文档发布后 Celery 异步任务

策略：
├── 短文档 (< 2000字)：LLM 全量生成摘要（~100字）
├── 中文档 (2000-8000字)：先语义分块，每块生成要点，LLM 汇总
└── 长文档 (> 8000字)：抽取关键段落 + 标题结构 + LLM 提炼

存储：
├── summary_text → 展示用
└── summary_vector → 摘要级语义搜索（可选）
```

### 5.3 智能推荐

```
推荐信号：
├── 阅读历史（协同过滤）
├── 文档向量相似度（内容推荐）
├── 同部门/同角色阅读趋势（热门推荐）
└── 用户显式收藏/点赞

冷启动策略：
├── 新用户 → 部门热门 + 全站热门
└── 新文档 → 相似文档读者 + 同分类订阅者

实现：
├── 离线层：Celery 定时任务每天计算用户嵌入向量 & 推荐列表
├── 在线层：API 直接读取预计算推荐 + 实时过滤（排除已读）
└── 初期算法：内容相似度 + 热门加权，后续迭代引入协同过滤
```

### 5.4 AI 配置项

```bash
# ── LLM 配置 ──
LLM_PROVIDER=openai_compatible       # openai | azure | local | ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=sk-xxxxxxxx
LLM_MODEL=qwen3:14b                  # 或 gpt-4o / deepseek-chat
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.3

# ── Embedding 配置 ──
EMBEDDING_MODEL=BAAI/bge-m3          # 本地加载 或 API
EMBEDDING_DEVICE=cuda                # cuda | cpu
EMBEDDING_DIM=768                    # BGE-M3 输出维度
EMBEDDING_BATCH_SIZE=32

# ── Reranker 配置 ──
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANKER_TOP_K=5                     # 精排后返回数
RERANKER_DEVICE=cuda

# ── 分块策略 ──
CHUNK_SIZE=512                       # 每块最大 token
CHUNK_OVERLAP=50                     # 块间重叠 token
CHUNK_METHOD=semantic                # semantic | fixed | recursive

# ── 推荐配置 ──
RECOMMEND_TOP_K=10                   # 每次推荐数量
RECOMMEND_REFRESH_CRON="0 3 * * *"  # 每天凌晨3点刷新
```

---

## 6. API 设计

### 6.1 路由总览

```
Base URL: /api/v1

── 认证 ──
POST   /auth/login                         # 本地登录
POST   /auth/refresh                       # 刷新 Token
GET    /auth/feishu/login-url              # 飞书 OAuth URL
GET    /auth/feishu/callback               # 飞书 OAuth 回调
GET    /auth/dingtalk/login-url            # 钉钉 OAuth URL
GET    /auth/dingtalk/callback             # 钉钉 OAuth 回调

── 文档管理 ──
GET    /documents                          # 文档列表（分页/筛选）
POST   /documents                          # 创建文档
GET    /documents/:id                      # 文档详情
PUT    /documents/:id                      # 更新文档
DELETE /documents/:id                      # 删除（软删除）
GET    /documents/:id/versions             # 版本历史
POST   /documents/:id/restore/:vid        # 回滚版本
GET    /documents/:id/comments             # 评论列表
POST   /documents/:id/comments             # 添加评论

── 智能搜索 ──
GET    /search                             # 混合搜索（keyword + semantic）
GET    /search/suggest                     # 搜索建议/自动补全
POST   /search/reindex                     # 重建索引（管理员）

── RAG 问答 ──
POST   /chat/ask                           # 基于知识库的问答（SSE 流式）
GET    /chat/history                       # 对话历史
DELETE /chat/history/:session_id           # 清除对话

── 智能摘要 ──
POST   /summarize/:document_id             # 为指定文档生成摘要
POST   /summarize/batch                    # 批量生成缺失摘要（管理员）

── 智能推荐 ──
GET    /recommend                          # 获取个人推荐列表
GET    /recommend/hot                      # 热门文档（全局）
GET    /recommend/similar/:document_id     # 相似文档

── 分类/标签 ──
GET    /categories                         # 分类树
POST   /categories                         # 创建分类
PUT    /categories/:id                     # 更新分类
DELETE /categories/:id                     # 删除分类
GET    /tags                               # 标签列表
POST   /tags                               # 创建标签

── 权限 ──
GET    /permissions/:type/:id              # 查询权限
PUT    /permissions/:type/:id              # 更新权限

── 集成管理（管理员）──
GET    /admin/integrations                 # 集成状态
PUT    /admin/integrations/feishu          # 飞书配置
PUT    /admin/integrations/dingtalk        # 钉钉配置
POST   /admin/integrations/feishu/sync-contacts
POST   /admin/integrations/dingtalk/sync-contacts
POST   /admin/integrations/feishu/import-docs
POST   /admin/integrations/dingtalk/import-docs

── 机器人回调 ──
POST   /webhooks/feishu/bot                # 飞书 Bot 事件
POST   /webhooks/dingtalk/bot              # 钉钉 Bot 事件

── 统计 ──
GET    /stats/overview                     # 总览
GET    /stats/documents                    # 文档统计
GET    /stats/users                        # 用户活跃
```

### 6.2 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

### 6.3 RAG 问答接口详情

**POST /api/v1/chat/ask**

```json
// Request
{
  "question": "公司年假政策是什么？",
  "session_id": "uuid (可选，用于多轮对话)",
  "top_k": 5
}

// Response (SSE 流式)
data: {"type": "thinking", "content": "正在检索相关知识..."}
data: {"type": "sources", "docs": [{"id": 1, "title": "年假制度", "score": 0.92}, ...]}
data: {"type": "answer", "content": "根据公司"}
data: {"type": "answer", "content": "《年假管理制度》"}
data: {"type": "done"}
```

---

## 7. 飞书/钉钉集成设计 🎯

### 7.1 集成架构

采用**策略模式**，定义统一抽象接口 `IntegrationProvider`：

```python
# backend/app/integrations/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExternalUser:
    external_id: str
    display_name: str
    email: Optional[str]
    avatar_url: Optional[str]
    mobile: Optional[str]
    department: Optional[str]

@dataclass
class ExternalDoc:
    external_id: str
    title: str
    content: str
    format: str          # "markdown" | "rich_text"
    created_at: str
    updated_at: str
    author: ExternalUser

class IntegrationProvider(ABC):
    """飞书/钉钉均实现此接口"""

    @abstractmethod
    async def get_auth_url(self, redirect_uri: str, state: str) -> str: ...

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> ExternalUser: ...

    @abstractmethod
    async def send_message(self, user_ids: list[str], content: str, msg_type: str = "text") -> bool: ...

    @abstractmethod
    async def send_card(self, user_ids: list[str], card: dict) -> bool: ...

    @abstractmethod
    async def sync_contacts(self) -> list[ExternalUser]: ...

    @abstractmethod
    async def import_documents(self, folder_id: str = None) -> list[ExternalDoc]: ...

    @abstractmethod
    async def verify_webhook_signature(self, headers: dict, body: bytes) -> bool: ...

    @abstractmethod
    def parse_webhook_event(self, body: dict) -> dict: ...
```

### 7.2 飞书接入清单

| 功能 | 飞书能力 | 说明 |
|---|---|---|
| **OAuth 登录** | 飞书 OAuth 2.0 | 前端跳转授权 → code 换 token |
| **通讯录同步** | 通讯录 API | 定时任务全量/增量同步 |
| **Bot 消息** | 飞书机器人 | 知识更新通知、@机器人搜索 |
| **消息卡片** | 飞书消息卡片 | 搜索结果/推荐以卡片推送 |
| **文档导入** | 云文档 API | 飞书 Doc → Markdown |
| **小程序/H5** | 飞书自定义应用 | 工作台嵌入 |

### 7.3 钉钉接入清单

| 功能 | 钉钉能力 | 说明 |
|---|---|---|
| **OAuth 登录** | 钉钉扫码/OAuth 2.0 | 与飞书同模式 |
| **通讯录同步** | 通讯录 API | 定时任务 |
| **Bot 消息** | 钉钉机器人 | Webhook + 回调 |
| **文档导入** | 钉钉文档 API | 钉钉 Doc 导入 |
| **微应用** | 钉钉微应用 | 工作台嵌入 |

### 7.4 用户来源映射

```sql
source VARCHAR(20) DEFAULT 'local',  -- local | feishu | dingtalk
external_id VARCHAR(128),            -- 外部平台 user_id
external_department VARCHAR(256),    -- 外部部门路径
```

匹配逻辑：`external_id + source` > `email` > 自动创建新用户。

---

## 8. 权限模型

### 8.1 RBAC + Resource 混合

```
User ──→ UserRole ──→ Role (super_admin / admin / editor / viewer)
  │
  └──→ Permission (直接赋权，覆盖角色默认权限)
        ├── resource_type: document | category
        ├── resource_id
        ├── role: reader | editor | admin
        ├── target_type: user | department | role
        └── target_id
```

**判断优先级**：直接赋权 > 部门权限 > 角色权限 > 默认（登录用户可读）

---

## 9. 部署方案（< 100 DAU）

### 9.1 推荐方案：单机 Docker Compose

```
一台服务器即可承载全部服务：

  CPU: 8 核+
  RAM: 32 GB+（含模型推理）
  GPU: 可选（有 GPU 则 Embedding/Reranker 更快，CPU 也能跑）
  SSD: 200 GB+
```

### 9.2 Docker Compose 编排

```yaml
# docker/docker-compose.prod.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: knowledge_base
      POSTGRES_USER: kb_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"  # 小规模
    volumes:
      - esdata:/usr/share/elasticsearch/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - miniodata:/data

  backend:
    build: ../backend
    depends_on: [postgres, redis, elasticsearch, minio]
    env_file:
      - ../.env
    ports:
      - "8000:8000"

  celery-worker:
    build: ../backend
    command: celery -A app.tasks worker -l info -c 4
    depends_on: [redis, postgres]
    env_file:
      - ../.env

  celery-beat:
    build: ../backend
    command: celery -A app.tasks beat -l info
    depends_on: [redis, postgres]
    env_file:
      - ../.env

  frontend:
    build: ../frontend
    ports:
      - "3000:3000"

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on: [backend, frontend]

volumes:
  pgdata:
  redisdata:
  esdata:
  miniodata:
```

---

## 10. 开发计划

| 阶段 | 内容 | 周期 |
|---|---|---|
| **Phase 1: 脚手架** | 项目初始化、DB 模型、认证（本地+飞书+钉钉 OAuth）、文档 CRUD、富文本编辑器 | 2 周 |
| **Phase 2: AI 核心** | Embedding 服务部署、文档向量化入库管道、混合搜索（ES+pgvector）、RAG 对话（SSE 流式） | 2 周 |
| **Phase 3: AI 增强** | 智能摘要生成、智能推荐（内容+协同）、Reranker 精排、搜索建议 | 1.5 周 |
| **Phase 4: 集成打通** | 飞书/钉钉 OAuth 登录、通讯录同步、Bot 消息推送、文档导入 | 2 周 |
| **Phase 5: 打磨** | 权限系统、统计面板、消息卡片、性能优化、测试完善 | 1.5 周 |

---

## 11. 待确认事项

| # | 问题 | 影响 |
|---|---|---|
| 1 | ~~是否要智能搜索/摘要/推荐~~ ✅ 已确认：全要，排入一期 | — |
| 2 | LLM 用哪家？（云端 OpenAI / 本地 Ollama+Qwen3 / 公司已有 API） | 影响成本和延迟 |
| 3 | GPU 资源有无？（Embedding + Reranker 模型推理） | CPU 也能跑但慢 5-10 倍 |
| 4 | 部署是纯内网还是可连外网？ | 影响模型下载和 API 调用 |
| 5 | 是否需要实时协同编辑（多人同时编辑同一文档）？ | 影响编辑器选型 |
| 6 | 飞书和钉钉是同时接还是先接一个？| 影响 Phase 4 排期 |

---

> **下一步**：确认后我立即搭建项目脚手架，开始 Phase 1 编码。
