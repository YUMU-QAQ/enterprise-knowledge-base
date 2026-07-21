"""Authentication & Security — JWT Token + Password hashing"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return bcrypt.hashpw(
        password.encode("utf-8")[:72], bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8")[:72],
        hashed_password.encode("utf-8"),
    )


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """Generate Access Token"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {"sub": str(subject), "iat": now, "exp": expire, "type": "access"}
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: str | int) -> str:
    """Generate Refresh Token"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    claims = {"sub": str(subject), "iat": now, "exp": expire, "type": "refresh"}
    return jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode token, returns None on failure"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
