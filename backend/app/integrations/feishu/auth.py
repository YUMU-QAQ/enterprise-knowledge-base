"""飞书 OAuth 认证"""

from app.core.config import settings
from app.integrations.base import ExternalUser, IntegrationProvider
from app.integrations.feishu.client import FeishuClient


class FeishuAuth(IntegrationProvider):
    """飞书认证实现"""

    source = "feishu"

    def __init__(self):
        self.client = FeishuClient()

    async def get_login_url(self, redirect_uri: str = "", state: str = "") -> str:
        """获取飞书 OAuth 授权 URL"""
        base = "https://open.feishu.cn/open-apis/authen/v1/authorize"
        params = f"app_id={settings.FEISHU_APP_ID}&redirect_uri={redirect_uri}"
        if state:
            params += f"&state={state}"
        return f"{base}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str = "") -> ExternalUser:
        """code 换取用户信息"""
        # Step 1: 获取 user_access_token
        data = await self.client.post(
            "/authen/v1/oidc/access_token",
            {
                "grant_type": "authorization_code",
                "code": code,
            },
        )
        if data.get("code") != 0:
            raise Exception(f"飞书 OAuth 失败: {data}")

        access_token = data["data"]["access_token"]

        # Step 2: 获取用户信息
        user_data = await self.client.get(
            "/authen/v1/user_info",
            params={"access_token": access_token},
        )
        if user_data.get("code") != 0:
            raise Exception(f"飞书获取用户信息失败: {user_data}")

        user = user_data["data"]
        return ExternalUser(
            external_id=user.get("open_id", ""),
            display_name=user.get("name", ""),
            email=user.get("email"),
            avatar_url=user.get("avatar_url"),
            mobile=user.get("mobile"),
        )

    async def send_message(self, user_id: str, content: str, msg_type: str = "text") -> bool:
        """发送消息"""
        data = await self.client.post(
            "/im/v1/messages",
            {
                "receive_id": user_id,
                "msg_type": msg_type,
                "content": content,
            },
            params={"receive_id_type": "open_id"},
        )
        return data.get("code") == 0

    async def send_card(self, user_id: str, card: dict) -> bool:
        """发送消息卡片"""
        import json
        return await self.send_message(user_id, json.dumps(card), msg_type="interactive")

    async def sync_contacts(self) -> list[ExternalUser]:
        raise NotImplementedError("通讯录同步暂未实现")

    async def import_documents(self, folder_id: str | None = None) -> list:
        raise NotImplementedError("文档导入暂未实现")

    async def verify_signature(self, headers: dict, body: bytes) -> bool:
        """验证飞书回调签名（简化实现）"""
        # TODO: 完整签名验证
        return True

    def parse_event(self, body: dict) -> dict:
        """解析飞书事件"""
        return body.get("event", body)
