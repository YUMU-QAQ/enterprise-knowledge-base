"""消息通知任务"""

from app.tasks import celery_app


@celery_app.task(name="handle_feishu_bot_event")
def handle_feishu_bot_event(event: dict):
    """处理飞书 Bot 事件"""
    import asyncio
    asyncio.run(_handle_feishu_bot_event(event))


async def _handle_feishu_bot_event(event: dict):
    from app.integrations.feishu.bot import FeishuBot
    bot = FeishuBot()
    await bot.handle_message(event)


@celery_app.task(name="handle_dingtalk_bot_event")
def handle_dingtalk_bot_event(event: dict):
    """处理钉钉 Bot 事件"""
    import asyncio
    asyncio.run(_handle_dingtalk_bot_event(event))


async def _handle_dingtalk_bot_event(event: dict):
    from app.integrations.dingtalk.bot import DingTalkBot
    bot = DingTalkBot()
    await bot.handle_message(event)


@celery_app.task(name="notify_document_published")
def notify_document_published(document_id: int, document_title: str, author_name: str):
    """文档发布通知 — 推送给订阅用户"""
    import asyncio
    asyncio.run(_notify_document_published(document_id, document_title, author_name))


async def _notify_document_published(document_id: int, document_title: str, author_name: str):
    from app.services.notification_svc import NotificationService
    svc = NotificationService()
    await svc.notify_document_published(document_id, document_title, author_name)
