"""RAG Q&A Service — retrieval-augmented generation"""

import json
import logging
from typing import AsyncGenerator

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service

    Pipeline: question embedding → hybrid recall → rerank → prompt → LLM stream
    Falls back gracefully when embedding/reranker models are unavailable.
    """

    async def ask_stream(
        self,
        question: str,
        session_id: str | None = None,
        top_k: int = 5,
        user_id: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Streaming RAG Q&A"""
        yield {"type": "thinking", "content": "正在理解问题..."}

        # 1. Try to vectorize question for semantic search
        fused_docs: list[dict] = []
        try:
            from app.ai.embedding import get_embedding_model
            model = get_embedding_model()
            question_vector = model.encode(question).tolist()

            yield {"type": "thinking", "content": "正在检索相关知识..."}

            async with async_session() as db:
                semantic_docs = await self._semantic_search(db, question_vector, top_k=10)
                keyword_docs = await self._keyword_search(question, top_k=10)
                fused_docs = self._rrf_fusion(semantic_docs, keyword_docs, k=20)
            logger.info(f"Semantic docs: {len(semantic_docs)}, keyword docs: {len(keyword_docs)}, fused: {len(fused_docs)}")
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}, falling back to keyword only")
            # Fallback: keyword search only
            keyword_docs = await self._keyword_search(question, top_k=top_k)
            fused_docs = keyword_docs

        # 2. Reranker (skip if unavailable)
        try:
            from app.ai.reranker import get_reranker
            reranker = get_reranker()
            if reranker is not None and len(fused_docs) > top_k and hasattr(reranker, 'predict'):
                yield {"type": "thinking", "content": "正在精排结果..."}
                pairs = [[question, d.get("content", d.get("title", ""))] for d in fused_docs]
                scores = reranker.predict(pairs)
                for i, score in enumerate(scores):
                    if i < len(fused_docs):
                        fused_docs[i]["rerank_score"] = float(score)
                fused_docs.sort(key=lambda d: d.get("rerank_score", 0), reverse=True)
        except Exception as e:
            logger.warning(f"Reranker failed: {e}, using raw scores")

        top_docs = fused_docs[:top_k]

        yield {
            "type": "sources",
            "docs": [{"id": d["id"], "title": d["title"], "score": d.get("rrf_score", d.get("keyword_score", 0))} for d in top_docs],
        }

        # 3. Build prompt and stream LLM response
        yield {"type": "thinking", "content": "正在生成回答..."}
        from app.ai.prompts import RAG_SYSTEM_PROMPT, RAG_USER_PROMPT

        # Build context string
        context_parts = []
        for i, doc in enumerate(top_docs, 1):
            title = doc.get("title", "Unknown")
            content = doc.get("content", doc.get("summary_text", ""))
            context_parts.append(f"[{i}] Source: {title}\n{content}")
        context = "\n\n---\n\n".join(context_parts)

        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": RAG_USER_PROMPT.format(context=context, question=question)},
        ]

        try:
            from app.ai.llm import get_llm
            llm = get_llm()
            yield {"type": "thinking", "content": f"正在调用 LLM ({len(top_docs)} 条参考文档)..."}
            stream = await llm.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield {"type": "answer", "content": content}
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            yield {"type": "error", "content": f"LLM 调用失败: {str(e)}"}

        yield {"type": "done"}

    async def _semantic_search(
        self, db: AsyncSession, vector: list[float], top_k: int = 10
    ) -> list[dict]:
        """pgvector semantic search"""
        try:
            # Use SQLAlchemy's cast + array syntax for pgvector compatibility
            vec_str = "[" + ",".join(str(v) for v in vector) + "]"
            query = text("""
                SELECT d.id, d.title,
                       COALESCE(d.summary_text, d.content_md, d.content, '') AS display_content,
                       d.category_id,
                       d.view_count, d.created_at, d.updated_at,
                       1 - (d.embedding <=> cast(:vec as vector)) AS similarity
                FROM documents d
                WHERE d.status = 'published' AND d.embedding IS NOT NULL
                ORDER BY d.embedding <=> cast(:vec as vector)
                LIMIT :limit
            """)
            result = await db.execute(query, {"vec": vec_str, "limit": top_k})
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
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def _keyword_search(self, question: str, top_k: int = 10) -> list[dict]:
        """ES keyword search, fallback to PG full-text search"""
        # Try ES first
        from app.services.search_svc import SearchService
        svc = SearchService()
        result = await svc.search(q=question, page=1, page_size=top_k)
        items = result.data or []
        if items:
            return [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "content": item.get("summary_text") or "",
                    "keyword_score": item.get("score", 0),
                }
                for item in items
            ]

        # Fallback: simple DB query
        try:
            from app.core.database import async_session
            from sqlalchemy import select
            from app.models.document import Document
            async with async_session() as db:
                stmt = (
                    select(Document)
                    .where(Document.status == "published")
                    .where(Document.content_md.ilike(f"%{question}%"))
                    .limit(top_k)
                )
                result = await db.execute(stmt)
                docs = result.scalars().all()
                return [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "content": (doc.content_md or "")[:500],
                        "keyword_score": 1.0,
                    }
                    for doc in docs
                ]
        except Exception:
            return []

    def _rrf_fusion(
        self,
        semantic_docs: list[dict],
        keyword_docs: list[dict],
        k: int = 60,
    ) -> list[dict]:
        """RRF (Reciprocal Rank Fusion)"""
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
        """Get chat history (stub)"""
        return APIResponse.ok(data=[])

    async def delete_history(self, session_id: str) -> None:
        """Clear chat session (stub)"""
        pass
