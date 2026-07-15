"""RAG 对话路由 — 基于知识库的智能问答"""

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import get_current_user_optional
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.search import ChatRequest

router = APIRouter()


@router.post("/ask")
async def chat_ask(body: ChatRequest):
    """RAG 问答（SSE 流式返回）

    流程: 问题向量化 → 混合召回 → Reranker 精排 → LLM 生成 → 流式输出
    """
    from app.services.rag_svc import RAGService
    rag = RAGService()
    return EventSourceResponse(rag.ask_stream(
        question=body.question,
        session_id=body.session_id,
        top_k=body.top_k,
    ))


@router.get("/history", response_model=APIResponse)
async def chat_history(
    session_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """获取对话历史"""
    from app.services.rag_svc import RAGService
    return await RAGService().get_history(session_id, page, page_size)


@router.delete("/history/{session_id}", response_model=APIResponse)
async def delete_chat_history(session_id: str):
    """清除对话会话"""
    from app.services.rag_svc import RAGService
    await RAGService().delete_history(session_id)
    return APIResponse.ok(message="对话已清除")
