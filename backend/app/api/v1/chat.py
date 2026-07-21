"""RAG Chat API — SSE streaming with error resilience"""

import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.schemas.common import APIResponse
from app.schemas.search import ChatRequest

router = APIRouter()


@router.post("/ask")
async def chat_ask(body: ChatRequest):
    """RAG Q&A with SSE streaming"""

    async def event_generator():
        try:
            from app.services.rag_svc import RAGService
            rag = RAGService()
            async for event in rag.ask_stream(
                question=body.question,
                session_id=body.session_id,
                top_k=body.top_k,
            ):
                yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}
        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "content": f"AI 服务暂时不可用：{str(e)}",
                }, ensure_ascii=False),
            }
            yield {"event": "message", "data": json.dumps({"type": "done"})}

    return EventSourceResponse(event_generator())


@router.get("/history", response_model=APIResponse)
async def chat_history(
    session_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """Get chat history"""
    from app.services.rag_svc import RAGService
    return await RAGService().get_history(session_id, page, page_size)


@router.delete("/history/{session_id}", response_model=APIResponse)
async def delete_chat_history(session_id: str):
    """Clear chat session"""
    from app.services.rag_svc import RAGService
    await RAGService().delete_history(session_id)
    return APIResponse.ok(message="Chat cleared")
