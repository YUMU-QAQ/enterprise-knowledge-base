"""飞书文档导入"""

from app.integrations.base import ExternalDoc, ExternalUser
from app.integrations.feishu.client import FeishuClient


class FeishuDocs:
    """飞书云文档导入"""

    def __init__(self):
        self.client = FeishuClient()

    async def import_from_folder(self, folder_token: str | None = None) -> list[ExternalDoc]:
        """从飞书知识空间导入文档

        Args:
            folder_token: 飞书文件夹 token，None 则从根目录导入
        """
        # 获取文档列表
        docs = await self._list_docs(folder_token)
        result = []

        for doc_meta in docs:
            content = await self._get_doc_content(doc_meta["token"])
            result.append(ExternalDoc(
                external_id=doc_meta["token"],
                title=doc_meta["title"],
                content=content,
                format="markdown",
                created_at=doc_meta.get("create_time", ""),
                updated_at=doc_meta.get("edit_time", ""),
            ))

        return result

    async def _list_docs(self, folder_token: str | None = None) -> list[dict]:
        """获取文档列表"""
        # 调用飞书云文档 API: GET /drive/v1/files
        data = await self.client.get(
            "/drive/v1/files",
            params={"folder_token": folder_token or "", "page_size": 100},
        )
        if data.get("code") == 0:
            return data["data"].get("files", [])
        return []

    async def _get_doc_content(self, doc_token: str) -> str:
        """获取飞书文档内容并转为 Markdown"""
        data = await self.client.get(
            f"/docx/v1/documents/{doc_token}/raw_content",
        )
        if data.get("code") == 0:
            # 简化处理：取纯文本
            content_data = data["data"].get("content", "")
            # TODO: 完整 Doc → Markdown 转换
            return str(content_data)
        return ""


class FeishuContacts:
    """飞书通讯录同步"""

    def __init__(self):
        self.client = FeishuClient()

    async def sync_all(self) -> list[ExternalUser]:
        """全量同步通讯录"""
        users = []
        dept_users = await self._get_dept_users()

        for u in dept_users:
            users.append(ExternalUser(
                external_id=u.get("open_id", ""),
                display_name=u.get("name", ""),
                email=u.get("email"),
                avatar_url=u.get("avatar", {}).get("avatar_240"),
                mobile=u.get("mobile"),
                department=u.get("department_names", [{}])[0].get("name") if u.get("department_names") else None,
            ))

        return users

    async def _get_dept_users(self, department_id: str | None = None, page_size: int = 100) -> list[dict]:
        """获取部门用户"""
        all_users = []
        page_token = ""

        while True:
            data = await self.client.get(
                "/contact/v3/users",
                params={
                    "department_id": department_id or "0",
                    "page_size": page_size,
                    "page_token": page_token,
                },
            )
            if data.get("code") != 0:
                break

            items = data["data"].get("items", [])
            all_users.extend(items)

            if not data["data"].get("has_more"):
                break
            page_token = data["data"].get("page_token", "")

        return all_users
