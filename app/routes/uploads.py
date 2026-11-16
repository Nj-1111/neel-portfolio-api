from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

from .. import storage

router = APIRouter()

# extension -> content type. The client's filename is trusted only to pick an
# extension out of this table; the stored name is always generated.
# SVG is deliberately excluded: it can carry script and would be served from
# the same origin as uploaded images.
ALLOWED = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}

MAX_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("", status_code=201)
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext or 'unknown'}'. Allowed: {', '.join(sorted(ALLOWED))}",
        )

    body = await file.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File larger than 10 MB")
    if not body:
        raise HTTPException(status_code=400, detail="File is empty")

    try:
        url = storage.save(body, ext, ALLOWED[ext])
    except storage.StorageError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {
        "url": url,
        "fileName": Path(file.filename or "").name,
        "size": len(body),
    }
