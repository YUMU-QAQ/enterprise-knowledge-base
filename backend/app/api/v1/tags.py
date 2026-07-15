"""标签管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.tag import Tag
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("", response_model=APIResponse)
async def list_tags(db: AsyncSession = Depends(get_db)):
    """获取全部标签"""
    result = await db.execute(select(Tag).order_by(Tag.name))
    tags = result.scalars().all()
    return APIResponse.ok(data=[
        {"id": t.id, "name": t.name, "color": t.color} for t in tags
    ])


@router.post("", response_model=APIResponse, status_code=201)
async def create_tag(
    name: str,
    color: str = "#1890ff",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建标签"""
    existing = await db.execute(select(Tag).where(Tag.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": 40901, "message": "标签名已存在"})

    tag = Tag(name=name, color=color)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return APIResponse.ok({"id": tag.id, "name": tag.name, "color": tag.color})
