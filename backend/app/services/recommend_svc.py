"""智能推荐服务"""

from sqlalchemy import select, text, func
from app.core.database import async_session
from app.models.document import Document
from app.models.read_history import ReadHistory


class RecommendService:
    """推荐引擎

    推荐信号:
    - 内容相似度（向量相似）
    - 阅读历史（协同过滤基础）
    - 热门趋势（同部门/全局）
    """

    async def get_personal_recommend(self, user_id: int, top_k: int = 10) -> list[dict]:
        """个人推荐"""
        async with async_session() as db:
            # 获取用户读过的文档
            read_result = await db.execute(
                select(ReadHistory.document_id)
                .where(ReadHistory.user_id == user_id)
                .order_by(ReadHistory.last_read_at.desc())
                .limit(20)
            )
            read_ids = [row[0] for row in read_result.fetchall()]

            if not read_ids:
                # 冷启动：返回热门
                return await self.get_hot(top_k)

            # 内容推荐：基于最近阅读文档的向量相似度
            try:
                query = text("""
                    WITH last_read AS (
                        SELECT embedding FROM documents
                        WHERE id = :last_read_id AND embedding IS NOT NULL
                        LIMIT 1
                    )
                    SELECT d.id, d.title, d.summary_text, d.view_count,
                           d.created_at, d.updated_at,
                           1 - (d.embedding <=> (SELECT embedding FROM last_read)) AS similarity
                    FROM documents d
                    WHERE d.status = 'published'
                      AND d.embedding IS NOT NULL
                      AND d.id != ALL(:exclude_ids)
                    ORDER BY d.embedding <=> (SELECT embedding FROM last_read)
                    LIMIT :limit
                """)
                result = await db.execute(query, {
                    "last_read_id": read_ids[0],
                    "exclude_ids": read_ids,
                    "limit": top_k,
                })
                rows = result.fetchall()
                if rows:
                    return [
                        {
                            "id": row[0],
                            "title": row[1],
                            "summary_text": row[2],
                            "view_count": row[3],
                            "created_at": str(row[4]) if row[4] else "",
                            "updated_at": str(row[5]) if row[5] else "",
                            "score": float(row[6]),
                            "reason": "content_similar",
                        }
                        for row in rows
                    ]
            except Exception:
                pass

            return await self.get_hot(top_k)

    async def get_hot(self, top_k: int = 10) -> list[dict]:
        """全站热门"""
        async with async_session() as db:
            result = await db.execute(
                select(Document)
                .where(Document.status == "published")
                .order_by(Document.view_count.desc())
                .limit(top_k)
            )
            docs = result.scalars().all()
            return [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "summary_text": doc.summary_text,
                    "view_count": doc.view_count,
                    "like_count": doc.like_count,
                    "created_at": str(doc.created_at),
                    "reason": "hot",
                }
                for doc in docs
            ]

    async def get_similar(self, document_id: int, top_k: int = 5) -> list[dict]:
        """相似文档（基于向量）"""
        async with async_session() as db:
            try:
                query = text("""
                    SELECT d.id, d.title, d.summary_text, d.view_count,
                           d.created_at, d.updated_at,
                           1 - (d.embedding <=> (SELECT embedding FROM documents WHERE id = :doc_id)) AS similarity
                    FROM documents d
                    WHERE d.status = 'published'
                      AND d.embedding IS NOT NULL
                      AND d.id != :doc_id
                    ORDER BY d.embedding <=> (SELECT embedding FROM documents WHERE id = :doc_id)
                    LIMIT :limit
                """)
                result = await db.execute(query, {
                    "doc_id": document_id,
                    "limit": top_k,
                })
                rows = result.fetchall()
                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "summary_text": row[2],
                        "view_count": row[3],
                        "created_at": str(row[4]) if row[4] else "",
                        "score": float(row[6]),
                    }
                    for row in rows
                ]
            except Exception:
                return []
