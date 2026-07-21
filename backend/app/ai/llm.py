"""LLM Client — OpenAI-compatible API (DeepSeek, GPT-4o, Qwen3, etc.)"""

from openai import AsyncOpenAI

from app.core.config import settings

_llm_instance: AsyncOpenAI | None = None


def get_llm() -> AsyncOpenAI:
    """Get LLM client (singleton)"""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance
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
    """Generic LLM call

    Args:
        messages: [{"role": "system/user/assistant", "content": "..."}]
        model: model name, defaults to settings
        temperature: temperature, defaults to settings
        max_tokens: max tokens, defaults to settings
        stream: enable streaming
    """
    client = get_llm()

    return await client.chat.completions.create(
        model=model or settings.LLM_MODEL,
        messages=messages,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        max_tokens=max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
        stream=stream,
    )
