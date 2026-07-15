"""Celery 异步任务"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "knowledge_base",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 30,  # 单任务最长 30 分钟
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])
