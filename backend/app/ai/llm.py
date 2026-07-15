"""LLM 调用封装 — 支持 OpenAI 兼容接口（GPT-4o / Qwen3 / DeepSeek 等）"""

from app.core.config import settings

_llm_instance = None


def get_llm():
    """获取 LLM 客户端（单例）"""
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    from openai import AsyncOpenAI

    _llm_instance = AsyncOpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )
    return _llm_instance


async def llm_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    stream: bool = False,
):
    """通用 LLM 调用

    Args:
        messages: 对话消息列表 [{"role": "system/user/assistant", "content": "..."}]
        model: 模型名称，默认使用配置
        temperature: 温度参数
        max_tokens: 最大 token 数
        stream: 是否流式返回
    """
    client = get_llm()

    if model is None:
        model = settings.LLM_MODEL
    if temperature is None:
        temperature = settings.LLM_TEMPERATURE
    if max_tokens is None:
        max_tokens = settings.LLM_MAX_TOKENS

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )

    if stream:
        return response  # 返回流对象，调用方需要 async for

    return response.choices[0].message.content


class LLMClient:
    """同步风格 LLM 客户端封装"""

    async def ainvoke(self, prompt: str, system_prompt: str | None = None) -> str:
        """单轮调用，返回完整回答"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await llm_chat(messages)

    async def astream(self, prompt: str, system_prompt: str | None = None):
        """流式调用"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await llm_chat(messages, stream=True)
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
