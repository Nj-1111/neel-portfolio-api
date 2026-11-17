from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from ..database import get_session, next_sort_order
from ..models import Project

router = APIRouter()


class ProjectCreate(BaseModel):
    category: str = ""
    title: str = ""
    desc: str = ""
    techs: str = ""
    links: List[Any] = []
    attachments: List[Any] = []
    pinned: bool = False
    sort_order: int = 0


class ProjectUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    techs: Optional[str] = None
    links: Optional[List[Any]] = None
    attachments: Optional[List[Any]] = None
    pinned: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("")
def list_projects(session: Session = Depends(get_session)):
    projects = session.exec(
        select(Project).order_by(Project.pinned.desc(), Project.sort_order)
    ).all()
    return projects


@router.post("", status_code=201)
def create_project(data: ProjectCreate, session: Session = Depends(get_session)):
    if not data.sort_order:
        data.sort_order = next_sort_order(session, Project)
    project = Project(id=str(uuid.uuid4()), created_at=utcnow(), **data.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.put("/{project_id}")
def update_project(project_id: str, data: ProjectUpdate, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    session.delete(project)
    session.commit()
    return {"ok": True}
