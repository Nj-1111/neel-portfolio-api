from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime, timezone
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from ..database import get_session
from ..models import ContactSubmission, ContactMethod, ContactInfo

router = APIRouter()


# --------------------------------------------------------------- submissions

class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    subject: str = ""
    message: str

    @field_validator("name", "message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("subject")
    @classmethod
    def trim(cls, v: str) -> str:
        return v.strip()


@router.post("", status_code=201)
def submit_contact(data: ContactCreate, session: Session = Depends(get_session)):
    item = ContactSubmission(
        id=str(uuid.uuid4()),
        created_at=utcnow(),
        name=data.name,
        email=str(data.email),
        subject=data.subject,
        message=data.message,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return {"ok": True, "id": item.id}


@router.get("")
def list_submissions(session: Session = Depends(get_session)):
    items = session.exec(
        select(ContactSubmission).order_by(ContactSubmission.created_at.desc())
    ).all()
    return items


@router.delete("/submissions/{item_id}")
def delete_submission(item_id: str, session: Session = Depends(get_session)):
    item = session.get(ContactSubmission, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Submission not found")
    session.delete(item)
    session.commit()
    return {"ok": True}


# ------------------------------------------------------------------- tagline

class TaglineUpdate(BaseModel):
    tagline: str = ""


@router.get("/info")
def get_info(session: Session = Depends(get_session)):
    item = session.exec(select(ContactInfo)).first()
    return item or {"tagline": ""}


@router.put("/info")
def update_info(data: TaglineUpdate, session: Session = Depends(get_session)):
    item = session.exec(select(ContactInfo)).first()
    if not item:
        item = ContactInfo(id=str(uuid.uuid4()))
    item.tagline = data.tagline
    item.updated_at = utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


# ------------------------------------------------------------------- methods

class MethodCreate(BaseModel):
    label: str = ""
    value: str = ""
    url: str = ""
    sort_order: int = 0


class MethodUpdate(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("/methods")
def list_methods(session: Session = Depends(get_session)):
    return session.exec(select(ContactMethod).order_by(ContactMethod.sort_order)).all()


@router.post("/methods", status_code=201)
def create_method(data: MethodCreate, session: Session = Depends(get_session)):
    item = ContactMethod(id=str(uuid.uuid4()), **data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/methods/{item_id}")
def update_method(item_id: str, data: MethodUpdate, session: Session = Depends(get_session)):
    item = session.get(ContactMethod, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Contact method not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/methods/{item_id}")
def delete_method(item_id: str, session: Session = Depends(get_session)):
    item = session.get(ContactMethod, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Contact method not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
