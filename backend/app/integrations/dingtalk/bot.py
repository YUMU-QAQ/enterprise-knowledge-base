"""钉钉 Bot 消息处理"""

from app.integrations.dingtalk.auth import DingTalkAuth


class DingTalkBot:
    """钉钉机器人 — 回调处理 + 消息搜索"""

    def __init__(self):
        self.auth = DingTalkAuth()

    async def verify_signature(self, headers: dict, body: bytes) -> bool:
        return await self.auth.verify_signature(headers, body)

    def parse_event(self, body: dict) -> dict:
        return self.auth.parse_event(body)

    async def handle_message(self, event: dict):
        """处理收到的消息"""
        msg_type = event.get("msgtype", event.get("type", ""))

        if msg_type == "text":
            content = event.get("text", {}).get("content", event.get("content", ""))
            sender_id = event.get("senderId", event.get("sender_id", ""))

            results = await self.auth.search_knowledge_base(content[:100])
            if results:
                from app.services.notification_svc import NotificationService
                svc = NotificationService()
                await svc.send_search_result_card(sender_id, "dingtalk", content, results)
            else:
                await self.send_message(sender_id, f"未找到与「{content}」相关的文档")

    async def send_message(self, user_id: str, content: str) -> bool:
        return await self.auth.send_message(user_id, content)

    async def send_card(self, user_id: str, card: dict) -> bool:
        return await self.auth.send_card(user_id, card)
