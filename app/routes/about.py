from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from ..database import get_session
from ..models import AboutArticle

router = APIRouter()

# "site" = about this site, "me" = about me. Anything else is rejected so a
# typo in a client cannot silently create a third orphan article.
SLUGS = {"site", "me"}


class AboutUpdate(BaseModel):
    cover_url: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[List[Any]] = None
    blocks: Optional[List[Any]] = None


def _check(slug: str) -> str:
    if slug not in SLUGS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown article '{slug}'. Expected one of: {', '.join(sorted(SLUGS))}",
        )
    return slug


@router.get("/{slug}")
def get_about(slug: str, session: Session = Depends(get_session)):
    _check(slug)
    item = session.exec(select(AboutArticle).where(AboutArticle.slug == slug)).first()
    return item or {"slug": slug, "cover_url": "", "title": "", "tags": [], "blocks": []}


@router.put("/{slug}")
def update_about(slug: str, data: AboutUpdate, session: Session = Depends(get_session)):
    _check(slug)
    item = session.exec(select(AboutArticle).where(AboutArticle.slug == slug)).first()
    if not item:
        item = AboutArticle(id=str(uuid.uuid4()), slug=slug)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    item.updated_at = utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
