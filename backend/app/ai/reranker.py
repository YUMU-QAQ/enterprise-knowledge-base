"""Reranker 服务 — 召回后精排"""

import threading
from app.core.config import settings

_reranker_model = None
_model_lock = threading.Lock()


def get_reranker():
    """获取 Reranker 模型（单例）

    加载 BGE-Reranker 用于召回结果精排。
    CPU 环境返回 None，跳过精排阶段。
    """
    global _reranker_model

    if _reranker_model is not None:
        return _reranker_model

    with _model_lock:
        if _reranker_model is not None:
            return _reranker_model

        try:
            from sentence_transformers import CrossEncoder
            _reranker_model = CrossEncoder(
                settings.RERANKER_MODEL,
                device=settings.RERANKER_DEVICE,
            )
        except Exception:
            _reranker_model = None  # 不可用时跳过

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
