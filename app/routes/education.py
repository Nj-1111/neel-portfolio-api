from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional
from pydantic import BaseModel
import uuid

from ..database import get_session, next_sort_order
from ..models import Education

router = APIRouter()


class EducationCreate(BaseModel):
    degree: str = ""
    school: str = ""
    period: str = ""
    notes: str = ""
    sort_order: int = 0


class EducationUpdate(BaseModel):
    degree: Optional[str] = None
    school: Optional[str] = None
    period: Optional[str] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("")
def list_education(session: Session = Depends(get_session)):
    return session.exec(select(Education).order_by(Education.sort_order)).all()


@router.post("", status_code=201)
def create_education(data: EducationCreate, session: Session = Depends(get_session)):
    if not data.sort_order:
        data.sort_order = next_sort_order(session, Education)
    item = Education(id=str(uuid.uuid4()), **data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/{item_id}")
def update_education(item_id: str, data: EducationUpdate, session: Session = Depends(get_session)):
    item = session.get(Education, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Education not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_education(item_id: str, session: Session = Depends(get_session)):
    item = session.get(Education, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Education not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
