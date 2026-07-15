"""文档 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """创建文档"""
    title: str = Field(min_length=1, max_length=500)
    content: str | None = None
    content_md: str | None = None
    format: str = Field(default="markdown", pattern="^(markdown|rich_text)$")
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    category_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list)


class DocumentUpdate(BaseModel):
    """更新文档"""
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    content_md: str | None = None
    format: str | None = Field(default=None, pattern="^(markdown|rich_text)$")
    status: str | None = Field(default=None, pattern="^(draft|published|archived)$")
    category_id: int | None = None
    tag_ids: list[int] | None = None
    change_log: str | None = Field(default=None, max_length=500)


class DocumentResponse(BaseModel):
    """文档详情返回"""
    id: int
    title: str
    content: str | None
    content_md: str | None
    summary_text: str | None
    format: str
    status: str
    view_count: int
    like_count: int
    category_id: int | None
    category_name: str | None = None
    created_by: int
    author_name: str | None = None
    tags: list[dict] = Field(default_factory=list)
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    """文档列表项"""
    id: int
    title: str
    summary_text: str | None
    format: str
    status: str
    view_count: int
    like_count: int
    category_id: int | None
    category_name: str | None = None
    created_by: int
    author_name: str | None = None
    tags: list[dict] = Field(default_factory=list)
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentVersionResponse(BaseModel):
    """版本历史返回"""
    id: int
    version_num: int
    change_log: str | None
    created_by: int | None
    creator_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
