"""通用 Schema — 分页、响应格式"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页请求参数"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    """分页元信息"""
    page: int
    page_size: int
    total: int
    total_pages: int


class APIResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = 0
    message: str = "success"
    data: T | None = None
    pagination: PaginationMeta | None = None

    @classmethod
    def ok(cls, data: T = None, pagination: PaginationMeta | None = None, message: str = "success") -> "APIResponse[T]":
        return cls(code=0, message=message, data=data, pagination=pagination)

    @classmethod
    def error(cls, code: int, message: str) -> "APIResponse":
        return cls(code=code, message=message, data=None)
