"""文档分块策略"""

from app.core.config import settings


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    method: str = "semantic",
) -> list[str]:
    """将文档切分为适合 Embedding 和检索的小块

    Args:
        text: 文档全文
        chunk_size: 每块最大 token 数（估算）
        chunk_overlap: 块间重叠 token 数
        method: 切分方式 — semantic | fixed | recursive

    Returns:
        文本块列表
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = settings.CHUNK_OVERLAP

    if method == "semantic":
        return _semantic_chunk(text, chunk_size, chunk_overlap)
    elif method == "recursive":
        return _recursive_chunk(text, chunk_size, chunk_overlap)
    else:
        return _fixed_chunk(text, chunk_size, chunk_overlap)


def _semantic_chunk(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """语义分块 — 按段落/标题自然分割"""
    # 先按 Markdown 标题分割
    sections = _split_by_headers(text)

    chunks = []
    current_chunk = ""
    current_len = 0

    for section in sections:
        # 大致估算 token 数（中文字约 1.5 字符/token，英文约 4 字符/token）
        est_tokens = len(section) // 2

        if current_len + est_tokens > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # 保留重叠部分
            overlap_text = current_chunk[-chunk_overlap * 2:] if len(current_chunk) > chunk_overlap * 2 else current_chunk
            current_chunk = overlap_text + "\n\n" + section
            current_len = len(current_chunk) // 2
        else:
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section
            current_len += est_tokens

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _split_by_headers(text: str) -> list[str]:
    """按 Markdown 标题分割"""
    import re
    sections = re.split(r'\n(?=#{1,6}\s)', text)
    return [s.strip() for s in sections if s.strip()]


def _fixed_chunk(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """固定大小分块"""
    chunks = []
    step = (chunk_size - chunk_overlap) * 2  # 字符步长

    start = 0
    while start < len(text):
        end = start + chunk_size * 2
        chunk = text[start:end]
        chunks.append(chunk)
        start += step

    return chunks


def _recursive_chunk(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """递归分块 — 先按大分隔符，再按小分隔符"""
    separators = ["\n\n", "\n", "。", ".", " "]
    return _recursive_split(text, separators, chunk_size, chunk_overlap)


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """递归按分隔符切割"""
    if not separators:
        return _fixed_chunk(text, chunk_size, chunk_overlap)

    sep = separators[0]
    if sep not in text:
        return _recursive_split(text, separators[1:], chunk_size, chunk_overlap)

    parts = text.split(sep)
    chunks = []
    current = ""

    for part in parts:
        test = current + (sep if current else "") + part
        if len(test) // 2 <= chunk_size:
            current = test
        else:
            if current:
                chunks.append(current)
            if len(part) // 2 > chunk_size:
                # 递归切分该部分
                sub_chunks = _recursive_split(part, separators[1:], chunk_size, chunk_overlap)
                chunks.extend(sub_chunks)
                current = ""
            else:
                current = part

    if current:
        chunks.append(current)

    return chunks
