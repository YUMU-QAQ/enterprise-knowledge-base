"""智能推荐路由"""

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("", response_model=APIResponse)
async def get_recommendations(
    top_k: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """获取个人推荐列表

    基于: 阅读历史 + 文档相似度 + 同部门热门
    """
    from app.services.recommend_svc import RecommendService
    items = await RecommendService().get_personal_recommend(
        user_id=current_user.id,
        top_k=top_k,
    )
    return APIResponse.ok(data=items)


@router.get("/hot", response_model=APIResponse)
async def get_hot(
    top_k: int = Query(default=10, ge=1, le=50),
    current_user=Depends(get_current_user_optional),
):
    """全站热门文档"""
    from app.services.recommend_svc import RecommendService
    items = await RecommendService().get_hot(top_k=top_k)
    return APIResponse.ok(data=items)


@router.get("/similar/{document_id}", response_model=APIResponse)
async def get_similar(
    document_id: int,
    top_k: int = Query(default=5, ge=1, le=20),
):
    """相似文档推荐（基于向量相似度）"""
    from app.services.recommend_svc import RecommendService
    items = await RecommendService().get_similar(document_id, top_k)
    return APIResponse.ok(data=items)
