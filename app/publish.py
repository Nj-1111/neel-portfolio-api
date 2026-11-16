"""Ask the web repo to rebuild after content changes.

The public site is a static export, so editing content in the admin changes the
database but not the deployed HTML. This fires a GitHub `repository_dispatch`
at the web repo, whose workflow rebuilds and republishes.

Deliberate choices:

* The call is made from the API, not the admin, so the GitHub token stays
  server-side instead of shipping inside a browser bundle.
* It runs *before* the response is returned. Lambda freezes the execution
  environment once a response is sent, so a background task would often never
  run. The timeout is short and failures never fail the user's save.
* Visitor contact submissions do not trigger a rebuild — they never appear on
  the public site.
"""
import json
import logging
import os
from urllib import error, request

log = logging.getLogger("publish")

GITHUB_TOKEN = os.getenv("GITHUB_DISPATCH_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_DISPATCH_REPO", "")  # "owner/neel-portfolio-web"
EVENT_TYPE = os.getenv("GITHUB_DISPATCH_EVENT", "content-updated")
# overridable so the dispatch can be pointed at a mock in tests
GITHUB_API_BASE = os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/")
TIMEOUT_SECONDS = 3

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# The visitor contact form itself. Exact match only: /api/contact/methods and
# /api/contact/info DO appear on the public site and must rebuild.
NO_REBUILD_EXACT = {"/api/contact"}
# Inbox management — deleting a message changes nothing public.
NO_REBUILD_PREFIX = ("/api/contact/submissions",)


def enabled() -> bool:
    return bool(GITHUB_TOKEN and GITHUB_REPO)


def _should_rebuild(method: str, path: str, status: int) -> bool:
    if method not in WRITE_METHODS:
        return False
    if status >= 400:
        return False
    normalised = path.rstrip("/") or "/"
    if normalised in NO_REBUILD_EXACT:
        return False
    if any(normalised.startswith(p) for p in NO_REBUILD_PREFIX):
        return False
    return True


def trigger() -> bool:
    """Fires the dispatch. Returns True if GitHub accepted it."""
    if not enabled():
        return False

    req = request.Request(
        f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/dispatches",
        data=json.dumps({"event_type": EVENT_TYPE}).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "neel-portfolio-api",
        },
    )
    try:
        with request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            resp.read()
        log.info("rebuild dispatched to %s", GITHUB_REPO)
        return True
    except error.HTTPError as e:
        # 401/403 = bad or under-scoped token; 404 = wrong repo name
        log.warning("rebuild dispatch rejected (%s): %s", e.code,
                    e.read().decode("utf-8", "replace")[:200])
    except error.URLError as e:
        log.warning("rebuild dispatch unreachable: %s", e.reason)
    return False


async def publish_middleware(request_, call_next):
    response = await call_next(request_)
    if _should_rebuild(request_.method, request_.url.path, response.status_code):
        trigger()  # never raises; a failed rebuild must not fail the save
    return response


def demo() -> None:
    """Self-check for the rebuild rules. Run: python -m app.publish"""
    cases = [
        ("PUT", "/api/landing/", 200, True),
        ("POST", "/api/projects/", 201, True),
        ("DELETE", "/api/projects/abc", 200, True),
        ("PUT", "/api/about/me", 200, True),
        ("POST", "/api/uploads/", 201, True),
        ("GET", "/api/projects/", 200, False),        # reads never rebuild
        ("POST", "/api/projects/", 401, False),       # failed writes never rebuild
        ("PUT", "/api/landing/", 500, False),
        ("POST", "/api/contact/", 201, False),        # visitor message
        ("POST", "/api/contact", 201, False),
        ("DELETE", "/api/contact/submissions/x", 200, False),
        ("POST", "/api/contact/methods", 201, True),  # but methods ARE on the site
    ]
    for method, path, status, expected in cases:
        actual = _should_rebuild(method, path, status)
        assert actual is expected, f"{method} {path} [{status}]: expected {expected}, got {actual}"
    print(f"rebuild rules ok: {len(cases)} cases")


if __name__ == "__main__":
    demo()
