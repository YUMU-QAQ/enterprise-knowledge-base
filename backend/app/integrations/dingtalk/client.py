"""钉钉 SDK 封装 — API 客户端"""

import httpx
from app.core.config import settings

DINGTALK_BASE_URL = "https://api.dingtalk.com"


class DingTalkClient:
    """钉钉 API 客户端"""

    def __init__(self):
        self.app_key = settings.DINGTALK_APP_KEY
        self.app_secret = settings.DINGTALK_APP_SECRET
        self.corp_id = settings.DINGTALK_CORP_ID
        self._access_token: str | None = None

    async def _get_token(self) -> str:
        """获取 access_token（自动缓存）"""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{DINGTALK_BASE_URL}/v1.0/oauth2/accessToken",
                params={"appKey": self.app_key, "appSecret": self.app_secret},
            )
            data = resp.json()
            if "accessToken" in data:
                self._access_token = data["accessToken"]
                return self._access_token
            raise Exception(f"钉钉 Token 获取失败: {data}")

    async def get(self, path: str, params: dict | None = None) -> dict:
        """GET 请求"""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{DINGTALK_BASE_URL}{path}",
                params=params,
                headers={
                    "x-acs-dingtalk-access-token": token,
                },
            )
            return resp.json()

    async def post(self, path: str, json_data: dict | None = None) -> dict:
        """POST 请求"""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DINGTALK_BASE_URL}{path}",
                json=json_data,
                headers={
                    "x-acs-dingtalk-access-token": token,
                },
            )
            return resp.json()
