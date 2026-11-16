from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from ..database import get_session
from ..models import LandingContent

router = APIRouter()


class LandingUpdate(BaseModel):
    badge: Optional[str] = None
    role: Optional[str] = None
    bio: Optional[str] = None
    socials: Optional[List[Any]] = None
    terminal_title: Optional[str] = None
    terminal_lines: Optional[List[Any]] = None
    footer: Optional[str] = None


@router.get("")
def get_landing(session: Session = Depends(get_session)):
    item = session.exec(select(LandingContent)).first()
    return item or {}


@router.put("")
def update_landing(data: LandingUpdate, session: Session = Depends(get_session)):
    item = session.exec(select(LandingContent)).first()
    if not item:
        item = LandingContent(id=str(uuid.uuid4()))
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    item.updated_at = utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
