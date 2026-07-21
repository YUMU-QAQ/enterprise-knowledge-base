"""一键修复：重新为已有文档生成 Embedding + 重建 ES 索引

运行方式：在 backend 目录执行
    .venv\Scripts\python -m scripts.fix_all_docs
"""
import asyncio, sys, os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.database import async_session
from app.models.document import Document
from app.ai.embedding import embed_text
from app.ai.splitter import chunk_text
from sqlalchemy import select, update
from app.services.search_svc import SearchService


async def fix_all():
    async with async_session() as db:
        result = await db.execute(
            select(Document).where(Document.status.in_(["published", "draft"]))
        )
        docs = result.scalars().all()
        print(f"Found {len(docs)} documents")

        svc = SearchService()

        for doc in docs:
            doc_id = doc.id
            title = doc.title
            content = doc.content_md or doc.content or ""
            summary = doc.summary_text or content[:500]
            cat_id = doc.category_id
            vc = doc.view_count or 0
            d_status = doc.status or "published"
            created_ts = str(doc.created_at)
            updated_ts = str(doc.updated_at)

            if not content.strip():
                print(f"  [{doc_id}] {title}: SKIP (no content)")
                continue

            # 1. Re-generate embedding
            chunks = chunk_text(content, method="semantic")
            if not chunks:
                print(f"  [{doc_id}] {title}: SKIP (no chunks)")
                continue

            text_to_embed = " ".join(chunks[:3])[:2000]
            try:
                embedding = await embed_text(text_to_embed)
                await db.execute(
                    update(Document).where(Document.id == doc_id).values(embedding=embedding)
                )
                await db.commit()
                dim = len(embedding)
                print(f"  [{doc_id}] {title}: embedding OK ({dim} dims)")
            except Exception as e:
                print(f"  [{doc_id}] {title}: embedding FAILED: {e}")
                await db.rollback()
                continue

            # 2. Re-index in ES
            doc_data = {
                "id": doc_id,
                "title": title,
                "content": content,
                "summary_text": summary,
                "category_id": cat_id,
                "category_name": None,
                "author_name": None,
                "tags": [],
                "status": d_status,
                "view_count": vc,
                "created_at": created_ts,
                "updated_at": updated_ts,
            }
            try:
                await svc.index_document(doc_data)
                print(f"  [{doc.id}] {doc.title}: ES index OK")
            except Exception as e:
                print(f"  [{doc.id}] {doc.title}: ES index FAILED: {e}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(fix_all())
