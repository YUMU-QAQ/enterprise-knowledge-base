"""智能摘要服务"""

from app.core.config import settings


class SummarizeService:
    """文档摘要生成"""

    async def generate(self, document_id: int) -> str | None:
        """为文档生成摘要"""
        from sqlalchemy import select
        from app.core.database import async_session
        from app.models.document import Document

        async with async_session() as db:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()

            if doc is None or not doc.content_md:
                return None

            text = doc.content_md

            # 根据文档长度选择策略
            if len(text) < 2000:
                summary = await self._summarize_full(text)
            elif len(text) < 8000:
                summary = await self._summarize_chunked(text)
            else:
                summary = await self._summarize_long(text)

            if summary:
                doc.summary_text = summary
                await db.commit()

            return summary

    async def _summarize_full(self, text: str) -> str:
        """短文档全量摘要"""
        from app.ai.llm import get_llm
        from app.ai.prompts import SUMMARY_SHORT_PROMPT

        llm = get_llm()
        prompt = SUMMARY_SHORT_PROMPT.format(text=text)
        return await llm.ainvoke(prompt)

    async def _summarize_chunked(self, text: str) -> str:
        """中文档分块摘要"""
        from app.ai.splitter import chunk_text
        from app.ai.llm import get_llm
        from app.ai.prompts import SUMMARY_CHUNK_PROMPT, SUMMARY_MERGE_PROMPT

        llm = get_llm()
        chunks = chunk_text(text, chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)

        # 每块生成要点
        points = []
        for chunk in chunks[:5]:  # 最多取前5块
            point = await llm.ainvoke(SUMMARY_CHUNK_PROMPT.format(text=chunk))
            points.append(point.strip())

        # 汇总
        merge_prompt = SUMMARY_MERGE_PROMPT.format(points="\n".join(f"- {p}" for p in points))
        return await llm.ainvoke(merge_prompt)

    async def _summarize_long(self, text: str) -> str:
        """长文档抽取关键段落 + LLM 提炼"""
        # 简化实现：取开头 + 各段落首句
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        key_sentences = []
        for i, para in enumerate(paragraphs):
            sentences = para.split("。")
            if sentences:
                key_sentences.append(sentences[0] + "。")
            if len(key_sentences) >= 10:
                break

        from app.ai.llm import get_llm
        from app.ai.prompts import SUMMARY_LONG_PROMPT

        llm = get_llm()
        prompt = SUMMARY_LONG_PROMPT.format(
            title="",
            key_content="\n".join(key_sentences),
        )
        return await llm.ainvoke(prompt)
