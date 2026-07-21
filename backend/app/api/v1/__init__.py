"""API v1 路由聚合"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.search import router as search_router
from app.api.v1.chat import router as chat_router
from app.api.v1.summarize import router as summarize_router
from app.api.v1.recommend import router as recommend_router
from app.api.v1.categories import router as categories_router
from app.api.v1.tags import router as tags_router
from app.api.v1.admin import router as admin_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.stats import router as stats_router
from app.api.v1.upload import router as upload_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(documents_router, prefix="/documents", tags=["Documents"])
router.include_router(search_router, prefix="/search", tags=["Search"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(summarize_router, prefix="/summarize", tags=["Summarize"])
router.include_router(recommend_router, prefix="/recommend", tags=["Recommend"])
router.include_router(categories_router, prefix="/categories", tags=["Categories"])
router.include_router(tags_router, prefix="/tags", tags=["Tags"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
router.include_router(stats_router, prefix="/stats", tags=["Stats"])
router.include_router(upload_router, prefix="/upload", tags=["Upload"])
