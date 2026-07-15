# 企业知识库 (Enterprise Knowledge Base)

面向企业内部的智能知识管理平台，支持语义搜索（RAG）、智能摘要、个性化推荐，预置飞书/钉钉接口。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 |
| 搜索 | Elasticsearch 8.x + pgvector |
| AI | LangChain + BGE-M3 + LLM (OpenAI 兼容) |
| 存储 | PostgreSQL 16 + Redis 7 + MinIO |

## 快速开始

### 1. 克隆并配置

```bash
cp .env.example .env
# 编辑 .env 修改密码和密钥
```

### 2. 启动基础设施

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 3. 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 5. 访问

- 前端: http://localhost:3000
- API 文档: http://localhost:8000/docs
- MinIO 控制台: http://localhost:9001

## 项目结构

```
enterprise-knowledge-base/
├── frontend/          # React 前端
├── backend/           # Python 后端
├── docker/            # Docker 编排 & Nginx 配置
├── docs/              # 文档
│   └── TECH_STACK.md  # 技术方案设计
├── scripts/           # 脚本
├── .env.example       # 环境变量模板
└── README.md
```

## 文档

- [技术方案设计](docs/TECH_STACK.md)
- [API 文档](http://localhost:8000/docs)（启动后端后访问）
- 飞书接入指南（待补充）
- 钉钉接入指南（待补充）
