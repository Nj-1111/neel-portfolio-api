from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from ..database import get_session
from ..models import ResumeFile

router = APIRouter()


class ResumeUpsert(BaseModel):
    content: Optional[str] = None
    file_url: Optional[str] = None


@router.get("")
def get_resume(session: Session = Depends(get_session)):
    item = session.exec(select(ResumeFile).order_by(ResumeFile.updated_at.desc())).first()
    return item or {}


@router.post("", status_code=201)
def upsert_resume(data: ResumeUpsert, session: Session = Depends(get_session)):
    item = session.exec(select(ResumeFile)).first()
    if not item:
        item = ResumeFile(id=str(uuid.uuid4()))
    # only touch what the caller actually sent, so saving the text body does
    # not wipe an uploaded PDF and vice versa
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    item.updated_at = utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
