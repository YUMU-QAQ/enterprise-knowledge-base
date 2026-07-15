"""分类管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.category import Category
from app.models.document import Document
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("", response_model=APIResponse[list[CategoryResponse]])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取分类树"""
    result = await db.execute(
        select(Category).order_by(Category.sort_order, Category.name)
    )
    categories = result.scalars().all()

    # 统计每个分类的文档数
    cat_doc_counts = {}
    for cat in categories:
        cnt = await db.execute(
            select(func.count()).select_from(Document).where(
                Document.category_id == cat.id, Document.status == "published"
            )
        )
        cat_doc_counts[cat.id] = cnt.scalar() or 0

    # 构建树形结构
    cat_map = {}
    roots = []
    for cat in categories:
        node = CategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon=cat.icon,
            parent_id=cat.parent_id,
            sort_order=cat.sort_order,
            children=[],
            document_count=cat_doc_counts.get(cat.id, 0),
            created_at=cat.created_at,
        )
        cat_map[cat.id] = node

    for cat in categories:
        node = cat_map[cat.id]
        if node.parent_id and node.parent_id in cat_map:
            cat_map[node.parent_id].children.append(node)
        else:
            roots.append(node)

    return APIResponse.ok(data=roots)


@router.post("", response_model=APIResponse[CategoryResponse], status_code=201)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建分类"""
    existing = await db.execute(select(Category).where(Category.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": 40901, "message": "分类标识已存在"})

    cat = Category(**body.model_dump())
    db.add(cat)
    await db.flush()
    await db.refresh(cat)

    return APIResponse.ok(CategoryResponse.model_validate(cat))


@router.put("/{cat_id}", response_model=APIResponse[CategoryResponse])
async def update_category(
    cat_id: int,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新分类"""
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "分类不存在"})

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cat, key, value)

    await db.flush()
    await db.refresh(cat)
    return APIResponse.ok(CategoryResponse.model_validate(cat))


@router.delete("/{cat_id}", response_model=APIResponse)
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除分类"""
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "分类不存在"})

    # 子分类上移
    children = await db.execute(select(Category).where(Category.parent_id == cat_id))
    for child in children.scalars().all():
        child.parent_id = cat.parent_id

    # 文档取消分类
    docs = await db.execute(select(Document).where(Document.category_id == cat_id))
    for doc in docs.scalars().all():
        doc.category_id = cat.parent_id

    await db.delete(cat)
    await db.flush()
    return APIResponse.ok(message="分类已删除")
