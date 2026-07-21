"""搜索服务 — Elasticsearch 全文检索 + pgvector 语义搜索"""

from math import ceil

from elasticsearch import AsyncElasticsearch
from sqlalchemy import select

from app.core.config import settings
from app.schemas.common import APIResponse, PaginationMeta


class SearchService:
    """混合搜索服务

    一期: ES 全文检索
    二期: + pgvector 语义搜索 + RRF 融合
    """

    ES_INDEX = "documents"

    def __init__(self):
        self.es = AsyncElasticsearch(
            hosts=[settings.ES_HOST],
            basic_auth=(settings.ES_USER, settings.ES_PASSWORD) if settings.ES_USER else None,
        )

    def _es_available(self) -> bool:
        """检查 ES 是否可用"""
        return True  # 延迟检测，在调用时处理

    async def search(
        self,
        q: str,
        page: int = 1,
        page_size: int = 20,
        category_id: int | None = None,
        tag: str | None = None,
        sort_by: str = "relevance",
    ) -> APIResponse:
        """全文搜索 — ES 优先，回退 PostgreSQL ILIKE"""
        items = []
        total = 0

        # Try ES first
        try:
            return await self._es_search(q, page, page_size, category_id, tag, sort_by)
        except Exception:
            pass  # Fallback to DB

        # Fallback: PostgreSQL ILIKE search
        return await self._db_search(q, page, page_size, category_id, sort_by)

    async def _es_search(
        self,
        q: str,
        page: int,
        page_size: int,
        category_id: int | None,
        tag: str | None,
        sort_by: str,
    ) -> APIResponse:
        """Elasticsearch 全文检索"""
        must_clauses = [
            {
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "content^2", "summary_text"],
                    "type": "best_fields",
                }
            }
        ]

        filters = [{"term": {"status": "published"}}]
        if category_id:
            filters.append({"term": {"category_id": category_id}})
        if tag:
            filters.append({"term": {"tags": tag}})

        sort = []
        if sort_by == "created_at":
            sort.append({"created_at": {"order": "desc"}})
        elif sort_by == "view_count":
            sort.append({"view_count": {"order": "desc"}})

        response = await self.es.search(
            index=self.ES_INDEX,
            body={
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filters,
                    }
                },
                "sort": sort or ["_score"],
                "from": (page - 1) * page_size,
                "size": page_size,
                "highlight": {
                    "fields": {
                        "title": {},
                        "content": {"fragment_size": 150, "number_of_fragments": 2},
                    }
                },
            },
        )

        hits = response["hits"]
        total = hits["total"]["value"]

        items = []
        for hit in hits["hits"]:
            src = hit["_source"]
            # Use content field for display, summary_text as fallback
            display_text = src.get("summary_text") or src.get("content", "")[:500]
            items.append({
                "id": src["id"],
                "title": src.get("title") or "未命名文档",
                "summary_text": display_text,
                "category_id": src.get("category_id"),
                "category_name": src.get("category_name"),
                "author_name": src.get("author_name"),
                "tags": src.get("tags", []),
                "view_count": src.get("view_count", 0),
                "created_at": src.get("created_at"),
                "updated_at": src.get("updated_at"),
                "highlight": hit.get("highlight", {}),
                "score": hit["_score"],
            })

        return APIResponse.ok(
            data=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=ceil(total / page_size) if total > 0 else 0,
            ),
        )

    async def _db_search(
        self,
        q: str,
        page: int,
        page_size: int,
        category_id: int | None,
        sort_by: str,
    ) -> APIResponse:
        """PostgreSQL 回退搜索 — ILIKE 全文匹配"""
        from app.core.database import async_session
        from app.models.document import Document
        from sqlalchemy import func, or_

        async with async_session() as db:
            base_q = select(Document).where(
                Document.status == "published",
                or_(
                    Document.title.ilike(f"%{q}%"),
                    Document.content_md.ilike(f"%{q}%"),
                    Document.summary_text.ilike(f"%{q}%"),
                ),
            )
            if category_id:
                base_q = base_q.where(Document.category_id == category_id)

            count_q = select(func.count()).select_from(base_q.subquery())
            total = (await db.execute(count_q)).scalar() or 0

            if sort_by == "created_at":
                base_q = base_q.order_by(Document.created_at.desc())
            elif sort_by == "view_count":
                base_q = base_q.order_by(Document.view_count.desc())

            base_q = base_q.offset((page - 1) * page_size).limit(page_size)
            result = await db.execute(base_q)
            docs = result.scalars().all()

            items = []
            for doc in docs:
                display_text = (doc.summary_text or (doc.content_md[:200] if doc.content_md else ""))
                items.append({
                    "id": doc.id,
                    "title": doc.title,
                    "summary_text": display_text,
                    "category_id": doc.category_id,
                    "category_name": None,
                    "author_name": None,
                    "tags": [],
                    "view_count": doc.view_count,
                    "created_at": str(doc.created_at) if doc.created_at else None,
                    "updated_at": str(doc.updated_at) if doc.updated_at else None,
                    "highlight": {},
                    "score": 1.0,
                })

            return APIResponse.ok(
                data=items,
                pagination=PaginationMeta(
                    page=page,
                    page_size=page_size,
                    total=total,
                    total_pages=ceil(total / page_size) if total > 0 else 0,
                ),
            )

    async def suggest(self, q: str, limit: int = 10) -> list[str]:
        """搜索建议"""
        try:
            response = await self.es.search(
                index=self.ES_INDEX,
                body={
                    "suggest": {
                        "title_suggest": {
                            "prefix": q,
                            "completion": {"field": "title.suggest", "size": limit},
                        }
                    }
                },
            )
            suggestions = response.get("suggest", {}).get("title_suggest", [])
            if suggestions:
                return [s["text"] for s in suggestions[0].get("options", [])]
        except Exception:
            pass
        return []

    async def index_document(self, doc_data: dict) -> None:
        """索引单个文档"""
        try:
            await self.es.index(
                index=self.ES_INDEX,
                id=str(doc_data["id"]),
                body=doc_data,
                refresh=True,
            )
        except Exception:
            pass

    async def delete_document(self, doc_id: int) -> None:
        """从索引中删除"""
        try:
            await self.es.delete(index=self.ES_INDEX, id=str(doc_id))
        except Exception:
            pass

    async def reindex_all(self) -> None:
        """重建全部索引 — 下发 Celery 任务"""
        from app.tasks.index_tasks import rebuild_es_index
        rebuild_es_index.delay()
