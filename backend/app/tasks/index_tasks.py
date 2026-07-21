"""搜索索引任务 — ES 索引 + 文档向量化"""

from app.tasks import celery_app
from app.core.database import async_session
from sqlalchemy import select
from app.models.document import Document


@celery_app.task(name="rebuild_es_index")
def rebuild_es_index():
    """重建 Elasticsearch 索引"""
    import asyncio
    asyncio.run(_rebuild_es_index())


async def _rebuild_es_index():
    """异步重建所有文档的 ES 索引"""
    from app.services.search_svc import SearchService
    svc = SearchService()

    async with async_session() as db:
        result = await db.execute(
            select(Document).where(Document.status.in_(["published", "draft"]))
        )
        docs = result.scalars().all()

        for doc in docs:
            doc_data = {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content_md or "",
                "summary_text": doc.summary_text or (doc.content_md[:500] if doc.content_md else ""),
                "category_id": doc.category_id,
                "category_name": doc.category.name if doc.category else "",
                "author_name": doc.author.display_name if doc.author else "",
                "tags": [dt.tag.name for dt in doc.tags_rel if dt.tag] if doc.tags_rel else [],
                "status": doc.status,
                "view_count": doc.view_count,
                "created_at": str(doc.created_at),
                "updated_at": str(doc.updated_at),
            }
            await svc.index_document(doc_data)


@celery_app.task(name="generate_embeddings")
def generate_embeddings(document_id: int):
    """为文档生成向量"""
    import asyncio
    asyncio.run(_generate_embeddings(document_id))


async def _generate_embeddings(document_id: int):
    """异步生成文档向量"""
    from app.ai.embedding import embed_text
    from app.ai.splitter import chunk_text

    async with async_session() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()

        if doc is None or not doc.content_md:
            return

        # 对文档内容进行 Embedding
        chunks = chunk_text(doc.content_md)
        if not chunks:
            return

        # 对全文取平均向量（简化方案）
        # 生产环境应为每个 chunk 独立向量并存入向量库
        embeddings = []
        for chunk in chunks[:10]:  # 最多取前 10 个 chunk
            emb = await embed_text(chunk)
            embeddings.append(emb)

        # 平均池化
        dim = len(embeddings[0])
        avg_embedding = [sum(col) / len(col) for col in zip(*embeddings)]

        doc.embedding = avg_embedding
        await db.commit()
