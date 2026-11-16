from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional
from pydantic import BaseModel
import uuid

from ..database import get_session
from ..models import Certification

router = APIRouter()


class CertCreate(BaseModel):
    badge: str = ""
    name: str = ""
    credential_id: str = ""
    sort_order: int = 0


class CertUpdate(BaseModel):
    badge: Optional[str] = None
    name: Optional[str] = None
    credential_id: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("")
def list_certs(session: Session = Depends(get_session)):
    return session.exec(select(Certification).order_by(Certification.sort_order)).all()


@router.post("", status_code=201)
def create_cert(data: CertCreate, session: Session = Depends(get_session)):
    item = Certification(id=str(uuid.uuid4()), **data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/{item_id}")
def update_cert(item_id: str, data: CertUpdate, session: Session = Depends(get_session)):
    item = session.get(Certification, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Certification not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_cert(item_id: str, session: Session = Depends(get_session)):
    item = session.get(Certification, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Certification not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
