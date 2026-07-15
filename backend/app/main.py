"""企业知识库 — FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    from app.ai.embedding import get_embedding_model
    if settings.EMBEDDING_DEVICE != "cpu":
        get_embedding_model()  # 预热 Embedding 模型
    yield
    # 关闭时


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="企业内部智能知识管理平台 API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(v1_router, prefix="/api/v1")


@app.get("/api/health", tags=["System"])
async def health_check():
    """健康检查"""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
