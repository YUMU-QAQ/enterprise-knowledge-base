"""搜索与 AI 对话 Schema"""

from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    """搜索请求"""
    q: str = Field(min_length=1, max_length=500)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    sort_by: str = Field(default="relevance", pattern="^(relevance|created_at|view_count)$")


class ChatRequest(BaseModel):
    """RAG 对话请求"""
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class ChatSource(BaseModel):
    """引用的知识来源"""
    id: int
    title: str
    score: float
    snippet: str | None = None


class SummarizeRequest(BaseModel):
    """摘要生成请求"""
    document_id: int


class BatchSummarizeRequest(BaseModel):
    """批量生成摘要"""
    document_ids: list[int] | None = None  # None = 所有缺失摘要的文档


class RecommendRequest(BaseModel):
    """推荐请求"""
    top_k: int = Field(default=10, ge=1, le=50)
    include_read: bool = False
