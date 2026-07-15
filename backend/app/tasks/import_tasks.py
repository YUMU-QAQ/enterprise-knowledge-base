"""外部导入任务 — 飞书/钉钉文档 + 通讯录"""

from app.tasks import celery_app


@celery_app.task(name="sync_feishu_contacts")
def sync_feishu_contacts():
    """同步飞书通讯录"""
    import asyncio
    asyncio.run(_sync_feishu_contacts())


async def _sync_feishu_contacts():
    from app.integrations.feishu.docs import FeishuContacts
    from app.core.database import async_session
    from sqlalchemy import select
    from app.models.user import User

    contacts = FeishuContacts()
    external_users = await contacts.sync_all()

    async with async_session() as db:
        for eu in external_users:
            # 查找或创建
            result = await db.execute(
                select(User).where(
                    User.source == "feishu",
                    User.external_id == eu.external_id,
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    username=f"feishu_{eu.external_id}",
                    email=eu.email,
                    display_name=eu.display_name,
                    avatar_url=eu.avatar_url,
                    mobile=eu.mobile,
                    source="feishu",
                    external_id=eu.external_id,
                    external_department=eu.department,
                )
                db.add(user)
            else:
                user.display_name = eu.display_name
                user.email = eu.email
                user.avatar_url = eu.avatar_url
                user.external_department = eu.department

        await db.commit()


@celery_app.task(name="sync_dingtalk_contacts")
def sync_dingtalk_contacts():
    """同步钉钉通讯录"""
    import asyncio
    asyncio.run(_sync_dingtalk_contacts())


async def _sync_dingtalk_contacts():
    from app.integrations.dingtalk.docs import DingTalkContacts
    from app.core.database import async_session
    from sqlalchemy import select
    from app.models.user import User

    contacts = DingTalkContacts()
    external_users = await contacts.sync_all()

    async with async_session() as db:
        for eu in external_users:
            result = await db.execute(
                select(User).where(
                    User.source == "dingtalk",
                    User.external_id == eu.external_id,
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    username=f"dingtalk_{eu.external_id}",
                    email=eu.email,
                    display_name=eu.display_name,
                    avatar_url=eu.avatar_url,
                    mobile=eu.mobile,
                    source="dingtalk",
                    external_id=eu.external_id,
                    external_department=eu.department,
                )
                db.add(user)
            else:
                user.display_name = eu.display_name
                user.email = eu.email
                user.avatar_url = eu.avatar_url
                user.external_department = eu.department

        await db.commit()


@celery_app.task(name="import_feishu_documents")
def import_feishu_documents(folder_token: str | None = None):
    """从飞书导入文档"""
    import asyncio
    asyncio.run(_import_feishu_documents(folder_token))


async def _import_feishu_documents(folder_token: str | None = None):
    from datetime import datetime, timezone
    from app.integrations.feishu.docs import FeishuDocs
    from app.core.database import async_session
    from app.models.document import Document

    feishu_docs = FeishuDocs()
    external_docs = await feishu_docs.import_from_folder(folder_token)

    async with async_session() as db:
        for ed in external_docs:
            doc = Document(
                title=ed.title,
                content_md=ed.content,
                content=ed.content,
                format="markdown",
                status="draft",
                created_by=1,  # 系统导入者
                updated_by=1,
                published_at=datetime.now(timezone.utc),
            )
            db.add(doc)

        await db.commit()


@celery_app.task(name="import_dingtalk_documents")
def import_dingtalk_documents(folder_id: str | None = None):
    """从钉钉导入文档"""
    import asyncio
    asyncio.run(_import_dingtalk_documents(folder_id))


async def _import_dingtalk_documents(folder_id: str | None = None):
    from datetime import datetime, timezone
    from app.integrations.dingtalk.docs import DingTalkDocs
    from app.core.database import async_session
    from app.models.document import Document

    dingtalk_docs = DingTalkDocs()
    external_docs = await dingtalk_docs.import_from_folder(folder_id)

    async with async_session() as db:
        for ed in external_docs:
            doc = Document(
                title=ed.title,
                content_md=ed.content,
                content=ed.content,
                format="markdown",
                status="draft",
                created_by=1,
                updated_by=1,
                published_at=datetime.now(timezone.utc),
            )
            db.add(doc)

        await db.commit()
