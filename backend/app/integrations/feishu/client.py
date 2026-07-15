"""飞书 SDK 封装 — API 客户端"""

import httpx
from app.core.config import settings

FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """飞书 API 客户端

    封装飞书开放平台 HTTP API 调用，包括 Token 管理。
    """

    def __init__(self):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self._tenant_access_token: str | None = None

    async def _get_tenant_token(self) -> str:
        """获取 tenant_access_token（自动缓存）"""
        if self._tenant_access_token:
            return self._tenant_access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            data = resp.json()
            if data.get("code") == 0:
                self._tenant_access_token = data["tenant_access_token"]
                return self._tenant_access_token
            raise Exception(f"飞书 Token 获取失败: {data}")

    async def get(self, path: str, params: dict | None = None) -> dict:
        """GET 请求"""
        token = await self._get_tenant_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FEISHU_BASE_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            return resp.json()

    async def post(self, path: str, json_data: dict | None = None) -> dict:
        """POST 请求"""
        token = await self._get_tenant_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FEISHU_BASE_URL}{path}",
                json=json_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            return resp.json()
