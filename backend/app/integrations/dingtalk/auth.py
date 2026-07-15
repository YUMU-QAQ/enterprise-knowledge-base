"""钉钉 OAuth 认证"""

from app.core.config import settings
from app.integrations.base import ExternalUser, IntegrationProvider
from app.integrations.dingtalk.client import DingTalkClient


class DingTalkAuth(IntegrationProvider):
    """钉钉认证实现"""

    source = "dingtalk"

    def __init__(self):
        self.client = DingTalkClient()

    async def get_login_url(self, redirect_uri: str = "", state: str = "") -> str:
        """获取钉钉 OAuth 授权 URL"""
        base = "https://login.dingtalk.com/oauth2/auth"
        params = (
            f"redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&client_id={settings.DINGTALK_APP_KEY}"
            f"&scope=openid"
            f"&prompt=consent"
        )
        if state:
            params += f"&state={state}"
        return f"{base}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str = "") -> ExternalUser:
        """code 换取用户信息"""
        # Step 1: code → access_token
        data = await self.client.post(
            "/v1.0/oauth2/userAccessToken",
            {
                "clientId": settings.DINGTALK_APP_KEY,
                "clientSecret": settings.DINGTALK_APP_SECRET,
                "code": code,
                "grantType": "authorization_code",
            },
        )
        access_token = data.get("accessToken", "")

        # Step 2: 获取用户信息
        user_data = await self.client.get(
            "/v1.0/contact/users/me",
            params={"access_token": access_token},
        )
        return ExternalUser(
            external_id=user_data.get("openId", ""),
            display_name=user_data.get("nick", ""),
            email=user_data.get("email"),
            avatar_url=user_data.get("avatarUrl"),
            mobile=user_data.get("mobile"),
        )

    async def send_message(self, user_id: str, content: str, msg_type: str = "text") -> bool:
        """发送消息 — 通过机器人 Webhook"""
        import httpx
        webhook = f"https://oapi.dingtalk.com/robot/send?access_token={settings.DINGTALK_TOKEN}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook, json={
                "msgtype": "text",
                "text": {"content": content},
            })
            return resp.json().get("errcode") == 0

    async def send_card(self, user_id: str, card: dict) -> bool:
        """发送消息卡片"""
        import httpx
        webhook = f"https://oapi.dingtalk.com/robot/send?access_token={settings.DINGTALK_TOKEN}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook, json=card)
            return resp.json().get("errcode") == 0

    async def sync_contacts(self) -> list[ExternalUser]:
        raise NotImplementedError("通讯录同步暂未实现")

    async def import_documents(self, folder_id: str | None = None) -> list:
        raise NotImplementedError("文档导入暂未实现")

    async def verify_signature(self, headers: dict, body: bytes) -> bool:
        """验证钉钉回调签名（简化实现）"""
        # TODO: 完整签名验证
        return True

    def parse_event(self, body: dict) -> dict:
        """解析钉钉事件"""
        return body.get("event", body)
