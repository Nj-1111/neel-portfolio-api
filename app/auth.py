"""Admin authentication.

Implemented as middleware rather than a per-route dependency on purpose: a new
write endpoint added later is protected automatically instead of relying on
someone remembering to decorate it.

Rules:
  * Any POST/PUT/PATCH/DELETE requires the admin token ...
  * ... except POST /api/contact/, which is the public contact form.
  * GET /api/contact/ returns visitor submissions (personal data) and is
    therefore also protected. Every other GET is public site content.
"""
import os
import secrets

from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import JSONResponse

load_dotenv()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
HEADER = "x-admin-token"

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths are compared with any trailing slash stripped, because Starlette's
# redirect_slashes runs after middleware and both spellings reach us.
PUBLIC_WRITES = {"/api/contact"}
PROTECTED_READS = {"/api/contact"}


def _normalise(path: str) -> str:
    return path.rstrip("/") or "/"


def _needs_auth(method: str, path: str) -> bool:
    path = _normalise(path)
    if method in WRITE_METHODS:
        # the public form posts to the collection root only; the nested
        # /api/contact/methods and /api/contact/submissions stay protected
        return path not in PUBLIC_WRITES
    if method == "GET":
        return path in PROTECTED_READS
    return False


def _authorised(request: Request) -> bool:
    supplied = request.headers.get(HEADER, "")
    if not ADMIN_TOKEN or not supplied:
        return False
    return secrets.compare_digest(supplied, ADMIN_TOKEN)


async def admin_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":  # CORS preflight carries no auth header
        return await call_next(request)

    if _needs_auth(request.method, request.url.path):
        if not ADMIN_TOKEN:
            return JSONResponse(
                status_code=503,
                content={"detail": "ADMIN_TOKEN is not configured on the server."},
            )
        if not _authorised(request):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid admin token."},
            )

    return await call_next(request)


def demo() -> None:
    """Self-check for the routing rules. Run: python -m app.auth"""
    cases = [
        # (method, path, needs_auth)
        ("GET", "/api/projects/", False),
        ("GET", "/api/about/me", False),
        ("GET", "/api/landing/", False),
        ("POST", "/api/contact/", False),       # public contact form
        ("POST", "/api/contact", False),        # same, no trailing slash
        ("GET", "/api/contact/", True),         # submissions are personal data
        ("GET", "/api/contact", True),
        ("POST", "/api/contact/methods", True),
        ("DELETE", "/api/contact/submissions/abc", True),
        ("POST", "/api/projects/", True),
        ("PUT", "/api/projects/abc", True),
        ("DELETE", "/api/projects/abc", True),
        ("PUT", "/api/about/me", True),
        ("PUT", "/api/landing/", True),
        ("POST", "/api/uploads/", True),
        ("GET", "/", False),
    ]
    for method, path, expected in cases:
        actual = _needs_auth(method, path)
        assert actual is expected, f"{method} {path}: expected {expected}, got {actual}"
    print(f"auth rules ok: {len(cases)} cases")


if __name__ == "__main__":
    demo()
