"""Embedding 服务 — 文档向量化"""

import threading
from app.core.config import settings

_embedding_model = None
_model_lock = threading.Lock()


def get_embedding_model():
    """获取 Embedding 模型（单例，线程安全）

    优先本地加载 sentence-transformers，失败则使用 OpenAI 兼容 API。
    """
    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    with _model_lock:
        if _embedding_model is not None:
            return _embedding_model

        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE,
            )
        except Exception:
            # 回退：使用 OpenAI 兼容 Embedding API
            _embedding_model = OpenAIEmbedding()
    return _embedding_model


class OpenAIEmbedding:
    """OpenAI 兼容 Embedding API 封装"""

    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.model = settings.EMBEDDING_MODEL

    def encode(self, texts: str | list[str]) -> "list[float] | list[list[float]]":
        """同步编码（简化：使用 asyncio.run 包装异步调用）"""
        import asyncio
        return asyncio.run(self.aencode(texts))

    async def aencode(self, texts: str | list[str]) -> "list[float] | list[list[float]]":
        """异步编码"""
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        resp = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        embeddings = [d.embedding for d in resp.data]

        return embeddings[0] if is_single else embeddings


async def embed_text(text: str) -> list[float]:
    """工具函数：将文本转为向量"""
    model = get_embedding_model()
    return model.encode(text).tolist()  # type: ignore[union-attr]


async def embed_texts(texts: list[str], batch_size: int | None = None) -> list[list[float]]:
    """工具函数：批量文本转向量"""
    if batch_size is None:
        batch_size = settings.EMBEDDING_BATCH_SIZE

    model = get_embedding_model()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        emb = model.encode(batch)
        all_embeddings.extend(emb.tolist() if hasattr(emb, 'tolist') else emb)

    return all_embeddings
