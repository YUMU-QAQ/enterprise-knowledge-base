"""通知服务 — 飞书/钉钉消息推送"""

from app.core.config import settings


class NotificationService:
    """消息通知编排"""

    async def notify_document_published(self, document_id: int, document_title: str, author_name: str):
        """文档发布通知"""
        # TODO: 根据订阅规则确定通知范围
        # 简化实现：通知所有活跃用户
        pass

    async def notify_mention(self, user_ids: list[str], document_title: str, commenter: str):
        """@提醒"""
        message = f"📄 {commenter} 在「{document_title}」中提到了你"

        if settings.FEISHU_ENABLED:
            from app.integrations.feishu.bot import FeishuBot
            bot = FeishuBot()
            for uid in user_ids:
                await bot.send_message(uid, message)

        if settings.DINGTALK_ENABLED:
            from app.integrations.dingtalk.bot import DingTalkBot
            bot = DingTalkBot()
            for uid in user_ids:
                await bot.send_message(uid, message)

    async def send_search_result_card(
        self,
        user_id: str,
        platform: str,  # "feishu" | "dingtalk"
        query: str,
        results: list[dict],
    ):
        """以消息卡片形式推送搜索结果"""
        if platform == "feishu" and settings.FEISHU_ENABLED:
            from app.integrations.feishu.bot import FeishuBot
            bot = FeishuBot()
            card = self._build_feishu_search_card(query, results)
            await bot.send_card(user_id, card)

        elif platform == "dingtalk" and settings.DINGTALK_ENABLED:
            from app.integrations.dingtalk.bot import DingTalkBot
            bot = DingTalkBot()
            card = self._build_dingtalk_search_card(query, results)
            await bot.send_card(user_id, card)

    def _build_feishu_search_card(self, query: str, results: list[dict]) -> dict:
        """构建飞书消息卡片"""
        elements = [
            {
                "tag": "markdown",
                "content": f"**🔍 搜索: {query}**\n共找到 {len(results)} 条结果",
            }
        ]
        for r in results[:5]:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📄 [{r['title']}]({r.get('url', '')})\n{r.get('summary_text', '')[:100]}",
                },
            })
            elements.append({"tag": "hr"})

        return {
            "header": {
                "title": {"tag": "plain_text", "content": f"搜索结果: {query}"},
                "template": "blue",
            },
            "elements": elements,
        }

    def _build_dingtalk_search_card(self, query: str, results: list[dict]) -> dict:
        """构建钉钉消息卡片"""
        # 钉钉卡片 JSON 格式
        return {
            "msgtype": "actionCard",
            "actionCard": {
                "title": f"搜索结果: {query}",
                "text": "\n\n".join(
                    f"### [{r['title']}]({r.get('url', '')})\n{r.get('summary_text', '')[:100]}"
                    for r in results[:5]
                ),
                "btnOrientation": "0",
            },
        }
