"""File storage.

Two backends, chosen by environment so local development needs no cloud
account and Lambda never touches its ephemeral filesystem:

  * SUPABASE_URL + SUPABASE_SERVICE_KEY set -> Supabase Storage
  * otherwise                               -> local ./uploads directory

Both return a URL suitable for putting straight into the database: an absolute
https:// URL from Supabase, or an API-relative "/uploads/x.png" locally. The
frontends' assetUrl() already handles both shapes.
"""
import os
import uuid
from pathlib import Path
from urllib import error, request as urlrequest

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "portfolio")

LOCAL_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


def using_supabase() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


class StorageError(RuntimeError):
    """Raised when the storage backend rejects an upload."""


def _put_supabase(stored_name: str, body: bytes, content_type: str) -> str:
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{stored_name}"
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "apikey": SUPABASE_SERVICE_KEY,
            "Content-Type": content_type,
            "x-upsert": "true",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            resp.read()
    except error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise StorageError(f"Supabase storage rejected the upload ({e.code}): {detail}") from e
    except error.URLError as e:
        raise StorageError(f"Could not reach Supabase storage: {e.reason}") from e

    # bucket must be public for these to resolve without a signed URL
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{stored_name}"


def _put_local(stored_name: str, body: bytes) -> str:
    LOCAL_UPLOAD_DIR.mkdir(exist_ok=True)
    (LOCAL_UPLOAD_DIR / stored_name).write_bytes(body)
    return f"/uploads/{stored_name}"


def save(body: bytes, ext: str, content_type: str) -> str:
    """Stores bytes under a generated name and returns the public URL.

    The client's filename is never used for the stored name — only the
    extension, which the caller has already validated against an allowlist.
    """
    stored_name = f"{uuid.uuid4().hex}{ext}"
    if using_supabase():
        return _put_supabase(stored_name, body, content_type)
    return _put_local(stored_name, body)
