"""搜索路由 — 混合搜索（全文 + 语义）"""

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user_optional
from app.schemas.common import APIResponse
from app.schemas.search import SearchParams

router = APIRouter()


@router.get("", response_model=APIResponse)
async def search(
    q: str = Query(min_length=1, max_length=500),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: int | None = Query(default=None),
    tag: str | None = Query(default=None),
    sort_by: str = Query(default="relevance"),
):
    """混合搜索

    一期：Elasticsearch 全文检索 + 权限过滤
    二期：加入 pgvector 语义搜索 + RRF 融合
    """
    from app.services.search_svc import SearchService
    return await SearchService().search(
        q=q,
        page=page,
        page_size=page_size,
        category_id=category_id,
        tag=tag,
        sort_by=sort_by,
    )


@router.get("/suggest", response_model=APIResponse)
async def suggest(q: str = Query(min_length=1, max_length=100)):
    """搜索建议 / 自动补全"""
    from app.services.search_svc import SearchService
    suggestions = await SearchService().suggest(q)
    return APIResponse.ok(data=suggestions)


@router.post("/reindex", response_model=APIResponse)
async def reindex():
    """重建全部索引（管理员操作）"""
    from app.services.search_svc import SearchService
    await SearchService().reindex_all()
    return APIResponse.ok(message="索引重建任务已下发")
