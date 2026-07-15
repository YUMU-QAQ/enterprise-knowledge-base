"""集成提供者抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExternalUser:
    """外部平台用户信息"""
    external_id: str
    display_name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    mobile: Optional[str] = None
    department: Optional[str] = None


@dataclass
class ExternalDoc:
    """外部平台文档"""
    external_id: str
    title: str
    content: str
    format: str = "markdown"  # markdown | rich_text
    created_at: str = ""
    updated_at: str = ""
    author: Optional[ExternalUser] = None


class IntegrationProvider(ABC):
    """集成提供者抽象基类

    飞书和钉钉各自实现此接口，业务层只依赖抽象，不依赖具体平台。
    """

    @property
    @abstractmethod
    def source(self) -> str:
        """标识来源: 'feishu' | 'dingtalk'"""
        ...

    @abstractmethod
    async def get_login_url(self, redirect_uri: str = "", state: str = "") -> str:
        """获取 OAuth 登录 URL"""
        ...

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str = "") -> ExternalUser:
        """OAuth code 换取用户信息"""
        ...

    @abstractmethod
    async def send_message(self, user_id: str, content: str, msg_type: str = "text") -> bool:
        """发送消息"""
        ...

    @abstractmethod
    async def send_card(self, user_id: str, card: dict) -> bool:
        """发送消息卡片"""
        ...

    @abstractmethod
    async def sync_contacts(self) -> list[ExternalUser]:
        """同步通讯录"""
        ...

    @abstractmethod
    async def import_documents(self, folder_id: Optional[str] = None) -> list[ExternalDoc]:
        """导入文档"""
        ...

    @abstractmethod
    async def verify_signature(self, headers: dict, body: bytes) -> bool:
        """验证 Webhook 回调签名"""
        ...

    @abstractmethod
    def parse_event(self, body: dict) -> dict:
        """解析 Webhook 事件"""
        ...

    async def search_knowledge_base(self, query: str, top_k: int = 5) -> list[dict]:
        """Bot 触发搜索知识库（通用实现）"""
        from app.services.search_svc import SearchService
        svc = SearchService()
        result = await svc.search(q=query, page=1, page_size=top_k)
        return result.data or []
