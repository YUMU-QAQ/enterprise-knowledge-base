"""Prompt 模板"""

# ── RAG 问答 ──

RAG_SYSTEM_PROMPT = """你是一个企业知识库助手。请根据提供的知识库内容回答用户的问题。

要求:
1. 只根据提供的知识内容回答，不要编造信息
2. 如果知识库中没有相关信息，请诚实告知"知识库中暂未找到相关内容"
3. 回答末尾列出引用的文档标题作为参考来源
4. 回答简洁专业，使用中文
"""

RAG_USER_PROMPT = """## 相关知识内容

{context}

## 用户问题

{question}

请基于上述知识内容回答问题。"""


def build_rag_prompt(question: str, documents: list[dict]) -> list[dict]:
    """构建 RAG 对话消息"""
    # 构建上下文
    context_parts = []
    for i, doc in enumerate(documents, 1):
        title = doc.get("title", "未知文档")
        content = doc.get("content", doc.get("summary_text", ""))
        context_parts.append(f"[{i}] 来源: {title}\n{content}")

    context = "\n\n---\n\n".join(context_parts)

    return [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": RAG_USER_PROMPT.format(
            context=context,
            question=question,
        )},
    ]


# ── 智能摘要 ──

SUMMARY_SHORT_PROMPT = """请为以下文档生成一段简洁的摘要（100字以内），捕获文档的核心观点:

---
{text}
---

摘要:"""

SUMMARY_CHUNK_PROMPT = """请用一句话概括以下段落的核心内容:

---
{text}
---

一句话概括:"""

SUMMARY_MERGE_PROMPT = """请将以下要点合并为一段连贯的摘要（100字以内）:

{points}

摘要:"""

SUMMARY_LONG_PROMPT = """请基于以下文档的关键内容生成摘要（100字以内）:

---
{key_content}
---

摘要:"""


# ── 搜索建议 ──

SEARCH_SUGGEST_PROMPT = """用户输入了搜索词: "{query}"

请提供5个相关的搜索建议（更具体或相关的搜索词），每行一个。"""
