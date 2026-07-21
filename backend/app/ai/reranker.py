"""Reranker service — retrieval result re-ranking"""

from app.core.config import settings

_reranker_model = None
_reranker_loaded = False


def get_reranker():
    """Get Reranker model (singleton).

    Loads BGE-Reranker for retrieval result re-ranking.
    On CPU or when loading fails, returns None to skip re-ranking.
    """
    global _reranker_model, _reranker_loaded

    if _reranker_loaded:
        return _reranker_model if _reranker_model is not False else None

    _reranker_loaded = True

    try:
        from sentence_transformers import CrossEncoder
        _reranker_model = CrossEncoder(
            settings.RERANKER_MODEL,
            device=settings.RERANKER_DEVICE,
        )
    except Exception:
        _reranker_model = False

    if _reranker_model is False:
        return None
    return _reranker_model


async def rerank(query: str, documents: list[dict], top_k: int | None = None) -> list[dict]:
    """对召回结果精排

    Args:
        query: 用户问题
        documents: 召回文档列表 [{"id": ..., "content": ...}, ...]
        top_k: 精排后返回数量

    Returns:
        精排后的文档列表
    """
    if top_k is None:
        top_k = settings.RERANKER_TOP_K

    model = get_reranker()
    if model is None:
        return documents[:top_k]

    # 构造 query-doc 对
    pairs = [[query, doc.get("content", doc.get("title", ""))] for doc in documents]
    scores = model.predict(pairs)

    # 排序
    for i, score in enumerate(scores):
        documents[i]["rerank_score"] = float(score)

    documents.sort(key=lambda d: d.get("rerank_score", 0), reverse=True)
    return documents[:top_k]
