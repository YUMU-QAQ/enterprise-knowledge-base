"""飞书 Bot 消息处理"""

from app.integrations.feishu.auth import FeishuAuth


class FeishuBot:
    """飞书机器人 — 回调处理 + 消息搜索"""

    def __init__(self):
        self.auth = FeishuAuth()

    async def verify_signature(self, headers: dict, body: bytes) -> bool:
        return await self.auth.verify_signature(headers, body)

    def parse_event(self, body: dict) -> dict:
        return self.auth.parse_event(body)

    async def handle_message(self, event: dict):
        """处理收到的消息

        支持:
        - @机器人搜索知识库
        - 交互卡片回调
        """
        msg_type = event.get("msg_type", event.get("type", ""))

        if msg_type == "text":
            content = event.get("text", event.get("content", ""))
            sender_id = event.get("sender", {}).get("open_id", event.get("sender_id", ""))

            # 搜索知识库
            results = await self.auth.search_knowledge_base(content[:100])
            if results:
                from app.services.notification_svc import NotificationService
                svc = NotificationService()
                await svc.send_search_result_card(sender_id, "feishu", content, results)
            else:
                await self.send_message(sender_id, f"未找到与「{content}」相关的文档")

    async def send_message(self, user_id: str, content: str) -> bool:
        """发送文本消息"""
        import json
        text_content = json.dumps({"text": content})
        return await self.auth.send_message(user_id, text_content, msg_type="text")

    async def send_card(self, user_id: str, card: dict) -> bool:
        """发送卡片消息"""
        return await self.auth.send_card(user_id, card)
