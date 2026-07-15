"""文档管理路由"""

from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_optional
from app.models.comment import Comment
from app.models.document import Document, DocumentVersion
from app.models.tag import DocumentTag, Tag
from app.models.user import User
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.document import (
    DocumentCreate,
    DocumentListItem,
    DocumentResponse,
    DocumentUpdate,
    DocumentVersionResponse,
)

router = APIRouter()


async def _doc_to_response(doc: Document) -> dict:
    """将 Document ORM 对象转为字典，包含关联数据"""
    author = None
    if doc.author:
        author = doc.author.display_name
    category_name = None
    if doc.category:
        category_name = doc.category.name
    tags_data = []
    if doc.tags_rel:
        for dt in doc.tags_rel:
            if dt.tag:
                tags_data.append({"id": dt.tag.id, "name": dt.tag.name, "color": dt.tag.color})

    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "content_md": doc.content_md,
        "summary_text": doc.summary_text,
        "format": doc.format,
        "status": doc.status,
        "view_count": doc.view_count,
        "like_count": doc.like_count,
        "category_id": doc.category_id,
        "category_name": category_name,
        "created_by": doc.created_by,
        "author_name": author,
        "tags": tags_data,
        "published_at": doc.published_at,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.get("", response_model=APIResponse[list[DocumentListItem]])
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    sort_by: str = Query(default="updated_at"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """文档列表（分页/筛选/排序）"""
    query = select(Document).options(
        joinedload(Document.author),
        joinedload(Document.category),
        selectinload(Document.tags_rel).joinedload(DocumentTag.tag),
    )

    # 非管理员只看到已发布 + 自己的文档
    if current_user is None or not current_user.is_super_admin:
        query = query.where(
            (Document.status == "published") |
            ((Document.created_by == current_user.id) if current_user else False) |
            ((Document.status == "published") if current_user is None else True)
        )
        # Simplification: non-logged-in users only see published
        if current_user is None:
            query = query.where(Document.status == "published")

    if category_id:
        query = query.where(Document.category_id == category_id)
    if status and current_user and current_user.is_super_admin:
        query = query.where(Document.status == status)

    if tag:
        query = query.where(
            Document.id.in_(
                select(DocumentTag.document_id).join(Tag).where(Tag.name == tag)
            )
        )

    # 排序
    sort_map = {
        "updated_at": Document.updated_at.desc(),
        "created_at": Document.created_at.desc(),
        "published_at": Document.published_at.desc(),
        "view_count": Document.view_count.desc(),
    }
    order_by = sort_map.get(sort_by, Document.updated_at.desc())
    query = query.order_by(order_by)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    documents = result.unique().scalars().all()

    items = []
    for doc in documents:
        data = await _doc_to_response(doc)
        items.append(DocumentListItem(**data))

    return APIResponse.ok(
        data=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        ),
    )


@router.post("", response_model=APIResponse[DocumentResponse], status_code=201)
async def create_document(
    body: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建文档"""
    from datetime import datetime, timezone

    doc = Document(
        title=body.title,
        content=body.content,
        content_md=body.content_md,
        format=body.format,
        status=body.status,
        category_id=body.category_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    if body.status == "published":
        doc.published_at = datetime.now(timezone.utc)

    db.add(doc)
    await db.flush()

    # 处理标签
    if body.tag_ids:
        for tag_id in body.tag_ids:
            db.add(DocumentTag(document_id=doc.id, tag_id=tag_id))

    # 创建初始版本
    db.add(DocumentVersion(
        document_id=doc.id,
        version_num=1,
        content=body.content or "",
        content_md=body.content_md,
        change_log="初始版本",
        created_by=current_user.id,
    ))

    await db.flush()
    await db.refresh(doc)

    # 重新加载带关联
    result = await db.execute(
        select(Document)
        .options(
            joinedload(Document.author),
            joinedload(Document.category),
            selectinload(Document.tags_rel).joinedload(DocumentTag.tag),
        )
        .where(Document.id == doc.id)
    )
    doc = result.unique().scalar_one()

    return APIResponse.ok(DocumentResponse(**(await _doc_to_response(doc))))


@router.get("/{doc_id}", response_model=APIResponse[DocumentResponse])
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """获取文档详情"""
    result = await db.execute(
        select(Document)
        .options(
            joinedload(Document.author),
            joinedload(Document.category),
            selectinload(Document.tags_rel).joinedload(DocumentTag.tag),
        )
        .where(Document.id == doc_id)
    )
    doc = result.unique().scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "文档不存在"})

    # 权限检查：非公开文档只能作者/管理员查看
    if doc.status != "published":
        if current_user is None or (doc.created_by != current_user.id and not current_user.is_super_admin):
            raise HTTPException(status_code=403, detail={"code": 40301, "message": "无权访问"})

    # 增加阅读计数
    doc.view_count += 1
    await db.flush()

    return APIResponse.ok(DocumentResponse(**(await _doc_to_response(doc))))


@router.put("/{doc_id}", response_model=APIResponse[DocumentResponse])
async def update_document(
    doc_id: int,
    body: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新文档"""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags_rel))
        .where(Document.id == doc_id)
    )
    doc = result.unique().scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "文档不存在"})

    if doc.created_by != current_user.id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "无权编辑"})

    # 更新字段
    update_data = body.model_dump(exclude_unset=True, exclude={"tag_ids"})
    for key, value in update_data.items():
        if value is not None:
            setattr(doc, key, value)

    doc.updated_by = current_user.id

    # 更新标签
    if body.tag_ids is not None:
        # 删除旧标签
        for dt in list(doc.tags_rel):
            await db.delete(dt)
        # 添加新标签
        for tag_id in body.tag_ids:
            db.add(DocumentTag(document_id=doc.id, tag_id=tag_id))

    await db.flush()
    await db.refresh(doc)

    result = await db.execute(
        select(Document)
        .options(
            joinedload(Document.author),
            joinedload(Document.category),
            selectinload(Document.tags_rel).joinedload(DocumentTag.tag),
        )
        .where(Document.id == doc.id)
    )
    doc = result.unique().scalar_one()

    return APIResponse.ok(DocumentResponse(**(await _doc_to_response(doc))))


@router.delete("/{doc_id}", response_model=APIResponse)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """软删除文档"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "文档不存在"})

    if doc.created_by != current_user.id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "无权删除"})

    doc.status = "archived"
    await db.flush()

    return APIResponse.ok(message="文档已归档")


@router.get("/{doc_id}/versions", response_model=APIResponse[list[DocumentVersionResponse]])
async def list_versions(doc_id: int, db: AsyncSession = Depends(get_db)):
    """获取版本历史"""
    result = await db.execute(
        select(DocumentVersion)
        .options(joinedload(DocumentVersion.creator))
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    )
    versions = result.unique().scalars().all()

    items = [
        DocumentVersionResponse(
            id=v.id,
            version_num=v.version_num,
            change_log=v.change_log,
            created_by=v.created_by,
            creator_name=v.creator.display_name if v.creator else None,
            created_at=v.created_at,
        )
        for v in versions
    ]
    return APIResponse.ok(data=items)


@router.get("/{doc_id}/comments", response_model=APIResponse)
async def list_comments(
    doc_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取评论列表"""
    query = (
        select(Comment)
        .options(joinedload(Comment.user))
        .where(Comment.document_id == doc_id, Comment.parent_id.is_(None))
        .order_by(Comment.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    comments = result.unique().scalars().all()

    return APIResponse.ok(
        data=[
            {
                "id": c.id,
                "content": c.content,
                "user_id": c.user_id,
                "user_name": c.user.display_name if c.user else None,
                "created_at": c.created_at,
            }
            for c in comments
        ],
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        ),
    )


@router.post("/{doc_id}/comments", response_model=APIResponse, status_code=201)
async def add_comment(
    doc_id: int,
    content: str,
    parent_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加评论"""
    comment = Comment(
        document_id=doc_id,
        user_id=current_user.id,
        content=content,
        parent_id=parent_id,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    return APIResponse.ok({"id": comment.id, "content": comment.content})
