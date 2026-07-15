"""统计路由"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("/overview", response_model=APIResponse)
async def overview(db: AsyncSession = Depends(get_db)):
    """总览统计"""
    total_docs = (await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "published")
    )).scalar() or 0

    total_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )).scalar() or 0

    total_views = (await db.execute(
        select(func.sum(Document.view_count)).where(Document.status == "published")
    )).scalar() or 0

    return APIResponse.ok(data={
        "total_documents": total_docs,
        "total_users": total_users,
        "total_views": total_views or 0,
    })


@router.get("/documents", response_model=APIResponse)
async def document_stats(db: AsyncSession = Depends(get_db)):
    """文档统计"""
    # 按状态统计
    draft_count = (await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "draft")
    )).scalar() or 0
    published_count = (await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "published")
    )).scalar() or 0

    # 按分类统计
    from app.models.category import Category
    cat_stats = []
    categories = (await db.execute(select(Category))).scalars().all()
    for cat in categories:
        cnt = (await db.execute(
            select(func.count()).select_from(Document).where(
                Document.category_id == cat.id, Document.status == "published"
            )
        )).scalar() or 0
        cat_stats.append({"category": cat.name, "count": cnt})

    return APIResponse.ok(data={
        "draft": draft_count,
        "published": published_count,
        "by_category": cat_stats,
    })


@router.get("/users", response_model=APIResponse)
async def user_stats(db: AsyncSession = Depends(get_db)):
    """用户统计"""
    # 按来源统计
    from sqlalchemy import text
    result = await db.execute(
        select(User.source, func.count()).where(User.is_active == True).group_by(User.source)
    )
    by_source = [{"source": row[0], "count": row[1]} for row in result.all()]

    total = sum(item["count"] for item in by_source)

    return APIResponse.ok(data={
        "total_active": total,
        "by_source": by_source,
    })
