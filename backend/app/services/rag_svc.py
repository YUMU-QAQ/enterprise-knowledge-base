"""RAG 问答服务 — 检索增强生成"""

import json
from typing import AsyncGenerator

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.schemas.common import APIResponse


class RAGService:
    """RAG 服务

    流程: 问题向量化 → 混合召回 → Reranker 精排 → Prompt 构建 → LLM 流式生成
    """

    async def ask_stream(
        self,
        question: str,
        session_id: str | None = None,
        top_k: int = 5,
        user_id: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """流式 RAG 问答"""
        from app.ai.embedding import get_embedding_model
        from app.ai.llm import get_llm

        # 1. 问题向量化
        yield {"type": "thinking", "content": "正在理解问题..."}
        model = get_embedding_model()
        question_vector = model.encode(question).tolist()

        # 2. 混合召回
        yield {"type": "thinking", "content": "正在检索相关知识..."}

        # 2a. pgvector 语义召回 Top-10
        async with async_session() as db:
            semantic_docs = await self._semantic_search(db, question_vector, top_k=10)

            # 2b. ES 关键词召回 Top-10（如果可用）
            keyword_docs = await self._keyword_search(question, top_k=10)

            # 2c. RRF 融合
            fused_docs = self._rrf_fusion(semantic_docs, keyword_docs, k=20)
            yield {
                "type": "sources",
                "docs": [{"id": d["id"], "title": d["title"], "score": d.get("rrf_score", 0)} for d in fused_docs[:top_k]],
            }

        # 3. Reranker 精排
        yield {"type": "thinking", "content": "正在精排结果..."}
        from app.ai.reranker import get_reranker
        reranker = get_reranker()
        if reranker and len(fused_docs) > top_k:
            pairs = [[question, d.get("content", d.get("title", ""))] for d in fused_docs]
            scores = reranker.compute_score(pairs)
            for i, score in enumerate(scores):
                if i < len(fused_docs):
                    fused_docs[i]["rerank_score"] = float(score)
            fused_docs.sort(key=lambda d: d.get("rerank_score", 0), reverse=True)

        top_docs = fused_docs[:top_k]

        # 4. 构建 Prompt
        yield {"type": "thinking", "content": "正在生成回答..."}
        from app.ai.prompts import build_rag_prompt
        prompt = build_rag_prompt(question, top_docs)

        # 5. LLM 流式生成
        llm = get_llm()
        full_answer = ""
        async for chunk in llm.astream(prompt):
            full_answer += chunk
            yield {"type": "answer", "content": chunk}

        yield {"type": "done"}

    async def _semantic_search(
        self, db: AsyncSession, vector: list[float], top_k: int = 10
    ) -> list[dict]:
        """pgvector 语义搜索"""
        try:
            query = text("""
                SELECT d.id, d.title, d.summary_text, d.category_id,
                       d.view_count, d.created_at, d.updated_at,
                       1 - (d.embedding <=> :vec) AS similarity
                FROM documents d
                WHERE d.status = 'published' AND d.embedding IS NOT NULL
                ORDER BY d.embedding <=> :vec
                LIMIT :limit
            """)
            result = await db.execute(query, {"vec": vector, "limit": top_k})
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "content": row[2] or "",
                    "category_id": row[3],
                    "view_count": row[4],
                    "created_at": str(row[5]) if row[5] else "",
                    "updated_at": str(row[6]) if row[6] else "",
                    "semantic_score": float(row[7]),
                }
                for row in rows
            ]
        except Exception:
            return []

    async def _keyword_search(self, question: str, top_k: int = 10) -> list[dict]:
        """ES 关键词搜索"""
        from app.services.search_svc import SearchService
        svc = SearchService()
        result = await svc.search(q=question, page=1, page_size=top_k)
        items = result.data or []
        return [
            {
                "id": item["id"],
                "title": item["title"],
                "content": item.get("summary_text", ""),
                "keyword_score": item.get("score", 0),
            }
            for item in items
        ]

    def _rrf_fusion(
        self,
        semantic_docs: list[dict],
        keyword_docs: list[dict],
        k: int = 60,
    ) -> list[dict]:
        """RRF (Reciprocal Rank Fusion) 混合排序"""
        doc_map = {}

        for rank, doc in enumerate(semantic_docs):
            did = doc["id"]
            if did not in doc_map:
                doc_map[did] = doc
            doc_map[did]["rrf_score"] = doc_map[did].get("rrf_score", 0) + 1 / (k + rank + 1)

        for rank, doc in enumerate(keyword_docs):
            did = doc["id"]
            if did not in doc_map:
                doc_map[did] = doc
            doc_map[did]["rrf_score"] = doc_map[did].get("rrf_score", 0) + 1 / (k + rank + 1)

        fused = list(doc_map.values())
        fused.sort(key=lambda d: d.get("rrf_score", 0), reverse=True)
        return fused

    async def get_history(self, session_id: str | None, page: int, page_size: int) -> APIResponse:
        """获取对话历史（简化版，实际应存入 Redis/DB）"""
        # TODO: 实现对话历史持久化
        return APIResponse.ok(data=[])

    async def delete_history(self, session_id: str) -> None:
        """清除对话会话"""
        # TODO: 实现
        pass
