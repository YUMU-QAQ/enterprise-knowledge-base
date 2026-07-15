"""认证路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.user import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter()


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """本地账号登录"""
    result = await db.execute(
        select(User).where(User.username == body.username, User.source == "local")
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40101, "message": "用户名或密码错误"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40101, "message": "账号已被禁用"},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return APIResponse.ok(
        TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )
    )


@router.post("/register", response_model=APIResponse[UserResponse])
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """本地注册"""
    existing = await db.execute(
        select(User).where(User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40901, "message": "用户名已存在"},
        )

    user = User(
        username=body.username,
        email=body.email,
        display_name=body.display_name,
        hashed_password=hash_password(body.password),
        source="local",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return APIResponse.ok(UserResponse.model_validate(user))


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """刷新 Token"""
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "Refresh Token 无效或已过期"},
        )

    user_id = int(payload.get("sub"))
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40101, "message": "用户不存在或已禁用"},
        )

    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)

    return APIResponse.ok(
        TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            user=UserResponse.model_validate(user),
        )
    )


@router.get("/me", response_model=APIResponse[UserResponse])
async def me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return APIResponse.ok(UserResponse.model_validate(current_user))


# ── 飞书 / 钉钉 OAuth 入口（预留）──

@router.get("/feishu/login-url")
async def feishu_login_url():
    """飞书 OAuth 登录 URL"""
    if not _should_enable("feishu"):
        raise HTTPException(status_code=501, detail={"code": 50001, "message": "飞书集成未启用"})
    from app.integrations.feishu.auth import FeishuAuth
    return APIResponse.ok({"url": await FeishuAuth().get_login_url()})


@router.get("/feishu/callback")
async def feishu_callback(code: str, state: str = "", db: AsyncSession = Depends(get_db)):
    """飞书 OAuth 回调"""
    if not _should_enable("feishu"):
        raise HTTPException(status_code=501, detail={"code": 50001, "message": "飞书集成未启用"})
    from app.integrations.feishu.auth import FeishuAuth
    return await _oauth_callback(FeishuAuth(), code, db)


@router.get("/dingtalk/login-url")
async def dingtalk_login_url():
    """钉钉 OAuth 登录 URL"""
    if not _should_enable("dingtalk"):
        raise HTTPException(status_code=501, detail={"code": 50001, "message": "钉钉集成未启用"})
    from app.integrations.dingtalk.auth import DingTalkAuth
    return APIResponse.ok({"url": await DingTalkAuth().get_login_url()})


@router.get("/dingtalk/callback")
async def dingtalk_callback(code: str, state: str = "", db: AsyncSession = Depends(get_db)):
    """钉钉 OAuth 回调"""
    if not _should_enable("dingtalk"):
        raise HTTPException(status_code=501, detail={"code": 50001, "message": "钉钉集成未启用"})
    from app.integrations.dingtalk.auth import DingTalkAuth
    return await _oauth_callback(DingTalkAuth(), code, db)


# ── 辅助函数 ──

def _should_enable(platform: str) -> bool:
    from app.core.config import settings
    if platform == "feishu":
        return settings.FEISHU_ENABLED and bool(settings.FEISHU_APP_ID)
    if platform == "dingtalk":
        return settings.DINGTALK_ENABLED and bool(settings.DINGTALK_APP_KEY)
    return False


async def _oauth_callback(auth_provider, code: str, db: AsyncSession):
    """通用 OAuth 回调处理"""
    from app.integrations.base import ExternalUser
    ext_user: ExternalUser = await auth_provider.exchange_code(code)

    # 查找或创建用户
    result = await db.execute(
        select(User).where(
            User.source == auth_provider.source,
            User.external_id == ext_user.external_id,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        # 尝试 email 匹配
        if ext_user.email:
            result = await db.execute(
                select(User).where(User.email == ext_user.email, User.source == "local")
            )
            user = result.scalar_one_or_none()
            if user:
                user.source = auth_provider.source
                user.external_id = ext_user.external_id

    if user is None:
        user = User(
            username=f"{auth_provider.source}_{ext_user.external_id}",
            email=ext_user.email,
            display_name=ext_user.display_name,
            avatar_url=ext_user.avatar_url,
            source=auth_provider.source,
            external_id=ext_user.external_id,
            external_department=ext_user.department,
        )
        db.add(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "账号已被禁用"})

    await db.flush()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token_str = create_refresh_token(user.id)

    return APIResponse.ok(
        TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user=UserResponse.model_validate(user),
        )
    )
