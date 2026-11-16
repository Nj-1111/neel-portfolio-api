from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional, Any
from pydantic import BaseModel
import uuid

from ..database import get_session
from ..models import Experience

router = APIRouter()


class ExperienceCreate(BaseModel):
    role: str = ""
    company: str = ""
    location: str = ""
    period: str = ""
    highlights: List[Any] = []
    pinned: bool = False
    sort_order: int = 0


class ExperienceUpdate(BaseModel):
    role: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    period: Optional[str] = None
    highlights: Optional[List[Any]] = None
    pinned: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("")
def list_experience(session: Session = Depends(get_session)):
    items = session.exec(
        select(Experience).order_by(Experience.pinned.desc(), Experience.sort_order)
    ).all()
    return items


@router.post("", status_code=201)
def create_experience(data: ExperienceCreate, session: Session = Depends(get_session)):
    item = Experience(id=str(uuid.uuid4()), **data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/{item_id}")
def update_experience(item_id: str, data: ExperienceUpdate, session: Session = Depends(get_session)):
    item = session.get(Experience, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Experience not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_experience(item_id: str, session: Session = Depends(get_session)):
    item = session.get(Experience, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Experience not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
