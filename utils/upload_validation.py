"""File upload validation: size and extension checks."""
import os
from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

async def validate_upload(
    file: UploadFile,
    allowed_extensions: list[str],
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> bytes:
    """Read and validate an uploaded file. Returns content bytes."""
    # Extension check
    safe_name = os.path.basename(file.filename or "")
    _, ext = os.path.splitext(safe_name)
    if ext.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    # Size check — read in chunks to avoid buffering unlimited data
    chunks = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)  # 64KB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_bytes // (1024*1024)}MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)
