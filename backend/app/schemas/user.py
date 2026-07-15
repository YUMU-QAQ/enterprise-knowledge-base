"""用户 Schema"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """创建用户（本地注册）"""
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=100)
    email: EmailStr | None = None
    display_name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    """本地登录"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户信息返回"""
    id: int
    username: str
    email: str | None
    display_name: str
    avatar_url: str | None
    source: str
    is_active: bool
    is_super_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """登录返回 Token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
