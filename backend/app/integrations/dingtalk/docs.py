"""钉钉文档导入"""

from app.integrations.base import ExternalDoc, ExternalUser
from app.integrations.dingtalk.client import DingTalkClient


class DingTalkDocs:
    """钉钉文档导入"""

    def __init__(self):
        self.client = DingTalkClient()

    async def import_from_folder(self, folder_id: str | None = None) -> list[ExternalDoc]:
        """从钉钉知识库导入文档"""
        docs = await self._list_docs(folder_id)
        result = []

        for doc_meta in docs:
            content = await self._get_doc_content(doc_meta.get("id", ""))
            result.append(ExternalDoc(
                external_id=doc_meta.get("id", ""),
                title=doc_meta.get("title", ""),
                content=content,
                format="markdown",
                created_at=doc_meta.get("createTime", ""),
                updated_at=doc_meta.get("modifiedTime", ""),
            ))

        return result

    async def _list_docs(self, folder_id: str | None = None) -> list[dict]:
        """获取文档列表"""
        # TODO: 对接钉钉知识库 API
        return []

    async def _get_doc_content(self, doc_id: str) -> str:
        """获取钉钉文档内容"""
        # TODO: 对接钉钉文档 API
        return ""


class DingTalkContacts:
    """钉钉通讯录同步"""

    def __init__(self):
        self.client = DingTalkClient()

    async def sync_all(self) -> list[ExternalUser]:
        """全量同步通讯录"""
        users = []
        dept_users = await self._get_dept_users()

        for u in dept_users:
            users.append(ExternalUser(
                external_id=u.get("userId", ""),
                display_name=u.get("name", ""),
                email=u.get("email"),
                avatar_url=u.get("avatar"),
                mobile=u.get("mobile"),
                department=u.get("deptName"),
            ))

        return users

    async def _get_dept_users(self, dept_id: int | None = None, size: int = 100) -> list[dict]:
        """获取部门用户列表"""
        all_users = []
        cursor = 0

        while True:
            params = {"cursor": cursor, "size": size}
            if dept_id:
                params["dept_id"] = dept_id

            data = await self.client.get("/topapi/user/listsimple", params=params)
            if data.get("errcode") != 0:
                break

            result = data.get("result", {}).get("list", [])
            all_users.extend(result)

            if not data.get("result", {}).get("has_more"):
                break
            cursor = data.get("result", {}).get("next_cursor", 0)

        return all_users
