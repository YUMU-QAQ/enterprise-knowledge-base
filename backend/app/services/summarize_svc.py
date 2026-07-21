"""Document summarization service"""

from app.core.config import settings


class SummarizeService:
    """Document summary generation"""

    async def generate(self, document_id: int) -> str | None:
        """Generate summary for a document"""
        from sqlalchemy import select
        from app.core.database import async_session
        from app.models.document import Document

        async with async_session() as db:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()

            if doc is None or not doc.content_md:
                return None

            text = doc.content_md

            # Choose strategy by document length
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

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM and return text response"""
        from app.ai.llm import get_llm
        llm = get_llm()
        resp = await llm.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
            stream=False,
        )
        return resp.choices[0].message.content or ""

    async def _summarize_full(self, text: str) -> str:
        """Short document: full summarization"""
        from app.ai.prompts import SUMMARY_SHORT_PROMPT
        return await self._call_llm(SUMMARY_SHORT_PROMPT.format(text=text))

    async def _summarize_chunked(self, text: str) -> str:
        """Medium document: chunked summarization"""
        from app.ai.splitter import chunk_text
        from app.ai.prompts import SUMMARY_CHUNK_PROMPT, SUMMARY_MERGE_PROMPT

        chunks = chunk_text(text, chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)

        points = []
        for chunk in chunks[:5]:
            point = await self._call_llm(SUMMARY_CHUNK_PROMPT.format(text=chunk))
            points.append(point.strip())

        merge_prompt = SUMMARY_MERGE_PROMPT.format(points="\n".join(f"- {p}" for p in points))
        return await self._call_llm(merge_prompt)

    async def _summarize_long(self, text: str) -> str:
        """Long document: extract key paragraphs then summarize"""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        key_sentences = []
        for para in paragraphs:
            sentences = para.split("。")
            if sentences:
                key_sentences.append(sentences[0] + "。")
            if len(key_sentences) >= 10:
                break

        from app.ai.prompts import SUMMARY_LONG_PROMPT
        prompt = SUMMARY_LONG_PROMPT.format(
            title="",
            key_content="\n".join(key_sentences),
        )
        return await self._call_llm(prompt)
