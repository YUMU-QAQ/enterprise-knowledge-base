"""管理接口路由"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter()


def _require_admin(current_user: User):
    """管理员权限校验"""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail={"code": 40301, "message": "需要管理员权限"})


@router.get("/integrations", response_model=APIResponse)
async def get_integrations_status(current_user: User = Depends(get_current_user)):
    """获取集成状态"""
    _require_admin(current_user)
    from app.core.config import settings
    return APIResponse.ok(data={
        "feishu": {
            "enabled": settings.FEISHU_ENABLED,
            "app_id": settings.FEISHU_APP_ID[:8] + "***" if settings.FEISHU_APP_ID else None,
        },
        "dingtalk": {
            "enabled": settings.DINGTALK_ENABLED,
            "app_key": settings.DINGTALK_APP_KEY[:8] + "***" if settings.DINGTALK_APP_KEY else None,
        },
    })


@router.put("/integrations/feishu", response_model=APIResponse)
async def update_feishu_config(
    app_id: str | None = None,
    app_secret: str | None = None,
    enabled: bool | None = None,
    current_user: User = Depends(get_current_user),
):
    """更新飞书配置（运行时生效，重启后失效，正式使用需更新 .env）"""
    _require_admin(current_user)
    from app.core.config import settings
    if enabled is not None:
        settings.FEISHU_ENABLED = enabled
    if app_id:
        settings.FEISHU_APP_ID = app_id
    if app_secret:
        settings.FEISHU_APP_SECRET = app_secret
    return APIResponse.ok(message="飞书配置已更新（运行时生效）")


@router.put("/integrations/dingtalk", response_model=APIResponse)
async def update_dingtalk_config(
    app_key: str | None = None,
    app_secret: str | None = None,
    enabled: bool | None = None,
    current_user: User = Depends(get_current_user),
):
    """更新钉钉配置"""
    _require_admin(current_user)
    from app.core.config import settings
    if enabled is not None:
        settings.DINGTALK_ENABLED = enabled
    if app_key:
        settings.DINGTALK_APP_KEY = app_key
    if app_secret:
        settings.DINGTALK_APP_SECRET = app_secret
    return APIResponse.ok(message="钉钉配置已更新（运行时生效）")


@router.post("/integrations/feishu/sync-contacts", response_model=APIResponse)
async def sync_feishu_contacts(current_user: User = Depends(get_current_user)):
    """同步飞书通讯录"""
    _require_admin(current_user)
    from app.integrations.feishu.contacts import FeishuContacts
    from app.tasks.import_tasks import sync_feishu_contacts
    task = sync_feishu_contacts.delay()
    return APIResponse.ok({"task_id": task.id, "message": "飞书通讯录同步已下发"})


@router.post("/integrations/dingtalk/sync-contacts", response_model=APIResponse)
async def sync_dingtalk_contacts(current_user: User = Depends(get_current_user)):
    """同步钉钉通讯录"""
    _require_admin(current_user)
    from app.tasks.import_tasks import sync_dingtalk_contacts
    task = sync_dingtalk_contacts.delay()
    return APIResponse.ok({"task_id": task.id, "message": "钉钉通讯录同步已下发"})


@router.post("/integrations/feishu/import-docs", response_model=APIResponse)
async def import_feishu_docs(
    folder_token: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """从飞书导入文档"""
    _require_admin(current_user)
    from app.tasks.import_tasks import import_feishu_documents
    task = import_feishu_documents.delay(folder_token)
    return APIResponse.ok({"task_id": task.id, "message": "飞书文档导入已下发"})


@router.post("/integrations/dingtalk/import-docs", response_model=APIResponse)
async def import_dingtalk_docs(
    folder_id: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """从钉钉导入文档"""
    _require_admin(current_user)
    from app.tasks.import_tasks import import_dingtalk_documents
    task = import_dingtalk_documents.delay(folder_id)
    return APIResponse.ok({"task_id": task.id, "message": "钉钉文档导入已下发"})
