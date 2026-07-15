"""摘要生成任务"""

from app.tasks import celery_app


@celery_app.task(name="generate_summary")
def generate_summary(document_id: int):
    """为单文档生成摘要"""
    import asyncio
    asyncio.run(_generate_summary(document_id))


async def _generate_summary(document_id: int):
    from app.services.summarize_svc import SummarizeService
    svc = SummarizeService()
    await svc.generate(document_id)


@celery_app.task(name="batch_generate_summaries")
def batch_generate_summaries(document_ids: list[int] | None = None):
    """批量生成缺失摘要"""
    import asyncio
    asyncio.run(_batch_generate_summaries(document_ids))


async def _batch_generate_summaries(document_ids: list[int] | None = None):
    from sqlalchemy import select
    from app.core.database import async_session
    from app.models.document import Document
    from app.services.summarize_svc import SummarizeService

    async with async_session() as db:
        query = select(Document).where(Document.content_md.isnot(None))
        if document_ids:
            query = query.where(Document.id.in_(document_ids))
        else:
            query = query.where(Document.summary_text.is_(None))

        result = await db.execute(query)
        docs = result.scalars().all()

        svc = SummarizeService()
        for doc in docs:
            await svc.generate(doc.id)
