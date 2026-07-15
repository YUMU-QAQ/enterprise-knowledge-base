"""智能摘要路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import Document
from app.schemas.common import APIResponse
from app.schemas.search import BatchSummarizeRequest, SummarizeRequest

router = APIRouter()


@router.post("/{document_id}", response_model=APIResponse)
async def summarize_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """为指定文档生成摘要（异步任务）"""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "文档不存在"})

    from app.tasks.summarize_tasks import generate_summary
    task = generate_summary.delay(document_id)

    return APIResponse.ok({
        "task_id": task.id,
        "message": "摘要生成任务已下发",
    })


@router.post("/batch", response_model=APIResponse)
async def batch_summarize(
    body: BatchSummarizeRequest = None,
    current_user=Depends(get_current_user),
):
    """批量生成缺失摘要（管理员）"""
    from app.tasks.summarize_tasks import batch_generate_summaries
    task = batch_generate_summaries.delay(body.document_ids if body else None)
    return APIResponse.ok({
        "task_id": task.id,
        "message": "批量摘要生成任务已下发",
    })
