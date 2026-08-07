from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".txt"}


async def save_evidence_file(upload: UploadFile) -> tuple[str, str, str]:
    """校验并保存证据文件，返回原始名称、访问路径和扩展名。"""
    original_name = Path(upload.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if not original_name or suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="仅支持 PDF、图片及 Word/TXT 文档",
        )

    settings = get_settings()
    content = await upload.read(settings.max_upload_size_mb * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="上传文件不能为空")
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件不能超过 {settings.max_upload_size_mb}MB",
        )

    storage_dir = Path(settings.upload_dir).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{suffix}"
    destination = storage_dir / stored_name
    destination.write_bytes(content)
    await upload.close()
    return original_name, f"/uploads/{stored_name}", suffix.lstrip(".")
