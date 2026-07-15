"""分类 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """创建分类"""
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = None
    parent_id: int | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """更新分类"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    icon: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    """分类返回"""
    id: int
    name: str
    slug: str
    description: str | None
    icon: str | None
    parent_id: int | None
    sort_order: int
    children: list["CategoryResponse"] = Field(default_factory=list)
    document_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
