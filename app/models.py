from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import JSON
from typing import Optional, List, Any
from datetime import datetime, timezone
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    category: str = ""
    title: str = ""
    desc: str = ""
    techs: str = ""
    links: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    attachments: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    pinned: bool = False
    sort_order: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class Experience(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    role: str = ""
    company: str = ""
    location: str = ""
    period: str = ""
    # [{title, desc, tags: []}]
    highlights: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    pinned: bool = False
    sort_order: int = 0


class Certification(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    badge: str = ""
    name: str = ""
    credential_id: str = ""
    sort_order: int = 0


class Education(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    degree: str = ""
    school: str = ""
    period: str = ""
    notes: str = ""
    sort_order: int = 0


class ResumeFile(SQLModel, table=True):
    __tablename__ = "resume_file"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    content: str = ""
    file_url: str = ""
    updated_at: datetime = Field(default_factory=utcnow)


class ContactInfo(SQLModel, table=True):
    """Singleton row holding the contact page tagline."""
    __tablename__ = "contact_info"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tagline: str = ""
    updated_at: datetime = Field(default_factory=utcnow)


class ContactMethod(SQLModel, table=True):
    __tablename__ = "contact_method"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    label: str = ""
    value: str = ""
    url: str = ""
    sort_order: int = 0


class AboutArticle(SQLModel, table=True):
    """One long-form article per slug ("site", "me")."""
    __tablename__ = "about_article"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    slug: str = Field(default="site", index=True)
    cover_url: str = ""
    title: str = ""
    tags: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    # [{type: 'paragraph'|'image', text, url, caption}]
    blocks: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utcnow)


class ContactSubmission(SQLModel, table=True):
    __tablename__ = "contact_submission"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = ""
    email: str = ""
    subject: str = ""
    message: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class LandingContent(SQLModel, table=True):
    """Singleton row holding the editable parts of the public landing page."""
    __tablename__ = "landing_content"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    badge: str = ""
    role: str = ""
    bio: str = ""
    # [{label, url, accent}]
    socials: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    terminal_title: str = ""
    # [{cmd, output: []}]
    terminal_lines: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    footer: str = ""
    updated_at: datetime = Field(default_factory=utcnow)
