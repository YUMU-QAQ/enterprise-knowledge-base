"""Webhook 回调路由 — 飞书/钉钉 Bot 事件接收"""

from fastapi import APIRouter, Request

from app.schemas.common import APIResponse

router = APIRouter()


@router.post("/feishu/bot", response_model=APIResponse)
async def feishu_bot_webhook(request: Request):
    """飞书 Bot 事件回调

    接收飞书推送的消息事件，处理后返回响应。
    支持: @机器人搜索知识库、消息卡片交互回调
    """
    from app.integrations.feishu.bot import FeishuBot
    bot = FeishuBot()

    body = await request.body()
    headers = dict(request.headers)

    # 验证签名
    if not await bot.verify_signature(headers, body):
        return APIResponse(code=40301, message="签名验证失败")

    # 解析事件
    event = bot.parse_event(await request.json())

    # 处理事件（异步，立即返回 200，实际处理入队列）
    from app.tasks.notify_tasks import handle_feishu_bot_event
    handle_feishu_bot_event.delay(event)

    return APIResponse.ok(message="received")


@router.post("/dingtalk/bot", response_model=APIResponse)
async def dingtalk_bot_webhook(request: Request):
    """钉钉 Bot 事件回调"""
    from app.integrations.dingtalk.bot import DingTalkBot
    bot = DingTalkBot()

    body = await request.body()
    headers = dict(request.headers)

    if not await bot.verify_signature(headers, body):
        return APIResponse(code=40301, message="签名验证失败")

    event = bot.parse_event(await request.json())

    from app.tasks.notify_tasks import handle_dingtalk_bot_event
    handle_dingtalk_bot_event.delay(event)

    return APIResponse.ok(message="received")
