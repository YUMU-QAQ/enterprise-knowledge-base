"""搜索服务 — Elasticsearch 全文检索 + pgvector 语义搜索"""

from math import ceil

from elasticsearch import AsyncElasticsearch

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

    async def search(
        self,
        q: str,
        page: int = 1,
        page_size: int = 20,
        category_id: int | None = None,
        tag: str | None = None,
        sort_by: str = "relevance",
    ) -> APIResponse:
        """全文搜索"""
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

        try:
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
        except Exception:
            # ES 不可用时返回空
            return APIResponse.ok(
                data=[],
                pagination=PaginationMeta(page=page, page_size=page_size, total=0, total_pages=0),
            )

        hits = response["hits"]
        total = hits["total"]["value"]

        items = []
        for hit in hits["hits"]:
            src = hit["_source"]
            items.append({
                "id": src["id"],
                "title": src.get("title", ""),
                "summary_text": src.get("summary_text", ""),
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
