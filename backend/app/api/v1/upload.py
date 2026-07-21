"""File upload and import API"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import Document, DocumentVersion
from app.models.user import User
from app.schemas.common import APIResponse
from app.utils.storage import upload_file as minio_upload

router = APIRouter()


async def _index_document_async(doc_id: int, content_md: str):
    """Index document for search: embedding + ES"""
    from app.ai.embedding import embed_text
    from app.ai.splitter import chunk_text
    from app.core.database import async_session
    from sqlalchemy import update

    # 1. Generate embedding
    chunks = chunk_text(content_md, method="semantic")
    if not chunks:
        return
    # Use concatenated first N chunks as document-level embedding
    text_to_embed = " ".join(chunks[:3])[:2000]
    try:
        embedding = await embed_text(text_to_embed)
    except Exception:
        return

    # 2. Store embedding in DB
    async with async_session() as db:
        await db.execute(
            update(Document).where(Document.id == doc_id).values(embedding=embedding)
        )
        await db.commit()

    # 3. Index in Elasticsearch
    try:
        from app.services.search_svc import SearchService
        svc = SearchService()
        await svc.index_document({
            "id": doc_id,
            "title": "",
            "content": content_md,
            "summary_text": "",
            "tags": [],
            "status": "published",
        })
    except Exception:
        pass

# Supported formats and their MIME types
ALLOWED_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


async def _parse_file(filename: str, data: bytes) -> str:
    """Parse uploaded file and return Markdown text content"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    filename_lower = filename.lower()

    # Plain text / Markdown
    if ext in ("txt", "md", "markdown"):
        return data.decode("utf-8", errors="replace")

    # CSV → Markdown table
    if ext == "csv":
        return _parse_csv(data)

    # PDF
    if ext == "pdf":
        return await _parse_pdf(data, filename)

    # Word (.docx)
    if ext == "docx":
        return _parse_docx(data)

    # Excel (.xlsx / .xls)
    if ext in ("xlsx", "xls"):
        return _parse_excel(data, ext)

    # Unknown — try plain text
    try:
        return data.decode("utf-8")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": f"不支持的文件格式: .{ext}"},
        )


def _parse_csv(data: bytes) -> str:
    """Parse CSV to Markdown table"""
    import csv
    from io import StringIO

    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(StringIO(text))
    rows = list(reader)
    if not rows:
        return ""

    # Build markdown table
    md_lines = []
    # Header
    md_lines.append("| " + " | ".join(rows[0]) + " |")
    md_lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    # Body
    for row in rows[1:]:
        # Pad row if shorter than header
        padded = row + [""] * (len(rows[0]) - len(row))
        md_lines.append("| " + " | ".join(padded[:len(rows[0])]) + " |")

    return "\n".join(md_lines)


async def _parse_pdf(data: bytes, filename: str) -> str:
    """Parse PDF to Markdown text"""
    try:
        from langchain_community.document_loaders import PyPDFLoader
        import tempfile, os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
            return "\n\n".join(p.page_content for p in pages if p.page_content.strip())
        finally:
            os.unlink(tmp_path)
    except ImportError:
        pass

    # Fallback: try PyPDF2
    try:
        from PyPDF2 import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts)
    except ImportError:
        raise HTTPException(
            status_code=400,
            detail={"code": 40002, "message": "PDF 解析需要安装 pypdf 或 PyPDF2"},
        )


def _parse_docx(data: bytes) -> str:
    """Parse Word (.docx) to Markdown text"""
    try:
        from docx import Document as DocxDoc
        from io import BytesIO

        doc = DocxDoc(BytesIO(data))
        parts = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                parts.append("")
                continue
            # Convert heading styles
            if para.style.name.startswith("Heading"):
                level = int(para.style.name.split()[-1]) if para.style.name.split()[-1].isdigit() else 1
                parts.append("#" * min(level, 6) + " " + text)
            else:
                parts.append(text)
        return "\n\n".join(parts)
    except ImportError:
        raise HTTPException(
            status_code=400,
            detail={"code": 40002, "message": "Word 解析需要安装 python-docx"},
        )


def _parse_excel(data: bytes, ext: str) -> str:
    """Parse Excel to Markdown table"""
    try:
        import pandas as pd
        from io import BytesIO

        if ext == "xls":
            df = pd.read_excel(BytesIO(data), engine="xlrd")
        else:
            df = pd.read_excel(BytesIO(data), engine="openpyxl")

        # Limit rows for display
        if len(df) > 100:
            df = df.head(100)

        # Fill NaN
        df = df.fillna("")

        # Build markdown table
        headers = [str(c) for c in df.columns]
        md_lines = ["| " + " | ".join(headers) + " |"]
        md_lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for _, row in df.iterrows():
            md_lines.append("| " + " | ".join(str(v) for v in row.values) + " |")

        return "\n".join(md_lines)
    except ImportError:
        raise HTTPException(
            status_code=400,
            detail={"code": 40002, "message": "Excel 解析需要安装 pandas, openpyxl"},
        )


@router.post("", response_model=APIResponse)
async def upload_document(
    file: UploadFile = File(...),
    category_id: int | None = Form(None),
    status: str = Form("published"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and import a document file

    Supported formats: PDF, Word (.docx), Excel (.xlsx/.xls), CSV, TXT, Markdown (.md)
    Max file size: 50MB
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "未选择文件"})

    # Validate extension
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES and file.filename.rsplit(".", 1)[-1].lower() not in ("xls", "markdown", "doc"):
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": f"不支持的文件格式: {ext}，支持的格式: {', '.join(ALLOWED_TYPES.keys())}"},
        )

    # Read file content
    file_data = await file.read()
    if len(file_data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "文件大小超过 50MB 限制"})

    # Parse file to Markdown
    try:
        content_md = await _parse_file(file.filename, file_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 50001, "message": f"文件解析失败: {str(e)}"},
        )

    if not content_md.strip():
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "文件中未提取到文本内容，请检查文件是否为空或为扫描版 PDF"},
        )

    # Upload to MinIO
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{current_user.id}_{file.filename}"
    try:
        await minio_upload(safe_name, file_data, file.content_type or "application/octet-stream")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 50002, "message": f"文件存储失败: {str(e)}"},
        )

    # Create document record
    title = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename
    doc = Document(
        title=title,
        content=content_md,
        content_md=content_md,
        format="markdown",
        status=status,
        category_id=category_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    if status == "published":
        doc.published_at = datetime.now(timezone.utc)

    db.add(doc)
    await db.flush()

    # Create initial version
    db.add(DocumentVersion(
        document_id=doc.id,
        version_num=1,
        content=content_md,
        content_md=content_md,
        change_log=f"从文件导入: {file.filename}",
        created_by=current_user.id,
    ))

    await db.flush()
    await db.refresh(doc)

    # 3. Async: trigger embedding + ES indexing
    try:
        await _index_document_async(doc.id, content_md)
    except Exception:
        pass  # Non-blocking — indexing can be retried later

    return APIResponse.ok(
        data={
            "id": doc.id,
            "title": doc.title,
            "filename": file.filename,
            "content_length": len(content_md),
            "status": doc.status,
            "created_at": str(doc.created_at),
        },
        message=f"文件 {file.filename} 导入成功",
    )
