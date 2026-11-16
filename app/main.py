from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from datetime import datetime, timezone
import os
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from .database import create_db_and_tables, migrate, engine
from .models import (
    Project, Experience, Certification, ContactInfo, ContactMethod, LandingContent,
)
from .routes import (
    projects, experience, certifications, education, resume, contact, about, uploads,
    landing,
)
from .auth import admin_auth_middleware
from .publish import publish_middleware
from . import storage, publish


SEED_PROJECTS = [
    {
        "category": "ML · FROM SCRATCH",
        "title": "GPT-152M — Decoder-Only Transformer",
        "desc": "A 152M-parameter decoder-only transformer trained from scratch on the FineWeb dataset, covering tokenization, pretraining and a live inference demo.",
        "techs": "PyTorch, Transformers",
        "links": [
            {"label": "Repo", "url": "https://github.com/Nj-1111/gpt-152m-fineweb"},
            {"label": "Live demo", "url": "https://huggingface.co/spaces/Nj-1111/gpt-152m-demo"},
        ],
        "pinned": True,
        "sort_order": 1,
    },
    {
        "category": "AWS · HIGH AVAILABILITY",
        "title": "Multi-Region AWS Infrastructure",
        "desc": "Designed a highly available, multi-region AWS architecture using auto scaling, load balancing, VPC peering and replicated RDS for resilience against regional failure.",
        "techs": "Auto Scaling, ALB, VPC Peering, RDS",
        "links": [],
        "pinned": False,
        "sort_order": 2,
    },
    {
        "category": "INFRASTRUCTURE AS CODE",
        "title": "Terraform-VPC",
        "desc": "A reusable Terraform module that provisions a production-ready AWS VPC with public/private subnets, routing and gateways from a single configuration.",
        "techs": "Terraform, AWS VPC",
        "links": [{"label": "Repo", "url": "https://github.com/Nj-1111/Terraform-VPC"}],
        "pinned": False,
        "sort_order": 3,
    },
    {
        "category": "NLP · TOKENIZATION",
        "title": "Copernicus Tokenizer",
        "desc": "A byte-pair-encoding tokenizer built from scratch and published for reuse, aimed at NLP preprocessing pipelines.",
        "techs": "Python, BPE",
        "links": [{"label": "On Hugging Face", "url": "https://huggingface.co/Nj-1111/Copernicus-Tokenizer"}],
        "pinned": False,
        "sort_order": 4,
    },
]

SEED_EXPERIENCE = [
    {
        "role": "AWS Cloud Engineer Intern",
        "company": "Workmates Core2Cloud",
        "location": "Kolkata, India",
        "period": "Aug 2026 – present",
        "highlights": [
            {
                "title": "Cost-optimized ML workloads",
                "desc": "Architecting cost-optimized ML workloads and highly available, multi-region infrastructure on AWS.",
                "tags": ["AWS", "Terraform", "Python", "Docker"],
            }
        ],
        "pinned": True,
        "sort_order": 1,
    }
]

SEED_CERTS = [
    {"badge": "Amazon Web Services", "name": "AWS Cloud Practitioner", "credential_id": "", "sort_order": 1},
    {"badge": "Amazon Web Services", "name": "AWS AI Practitioner", "credential_id": "", "sort_order": 2},
]

SEED_CONTACT_METHODS = [
    {"label": "Email", "value": "neelbosen.jr21@gmail.com", "url": "mailto:neelbosen.jr21@gmail.com", "sort_order": 1},
    {"label": "GitHub", "value": "Nj-1111", "url": "https://github.com/Nj-1111", "sort_order": 2},
    {"label": "LinkedIn", "value": "neel-bose", "url": "https://www.linkedin.com/in/neel-bose-545bb921a/", "sort_order": 3},
    {"label": "Location", "value": "Kolkata, India", "url": "", "sort_order": 4},
]

SEED_LANDING = {
    "badge": "AVAILABLE FOR AWS · CLOUD · ML INFRA ROLES",
    "role": "AI Cloud Engineer",
    "bio": (
        "Final year engineer architecting cost-optimized ML workloads and highly available, "
        "multi-region infrastructure on AWS. I learn by breaking systems, then rebuilding "
        "them with decoupled architecture and pipelines."
    ),
    "socials": [
        {"label": "GitHub ↗", "url": "https://github.com/Nj-1111", "accent": True},
        {"label": "Hugging Face ↗", "url": "https://huggingface.co/Nj-1111", "accent": False},
        {"label": "Medium ↗", "url": "https://medium.com/@neelbosen.jr21", "accent": False},
        {"label": "LinkedIn ↗", "url": "https://www.linkedin.com/in/neel-bose-545bb921a/", "accent": False},
    ],
    "terminal_title": "neel@kolkata: ~",
    "terminal_lines": [
        {"cmd": "whoami", "output": ["neel bose — ai cloud engineer"]},
        {"cmd": "cat now.txt", "output": ["AWS Cloud Engineer Intern", "@ Workmates Core2Cloud", "since August 2026"]},
        {"cmd": "cat stack.txt", "output": ["AWS · Terraform · Python · Docker", "PyTorch · LangGraph · Linux"]},
        {"cmd": "certs --list", "output": ["AWS Cloud Practitioner", "AWS AI Practitioner"]},
    ],
    "footer": "© 2026 NEEL BOSE · KOLKATA, INDIA",
}

SEED_TAGLINE = (
    "Open to AWS, cloud and ML infrastructure roles. "
    "The fastest way to reach me is email — I usually reply within a day."
)


def seed_data():
    with Session(engine) as session:
        if not session.exec(select(Project)).first():
            for p in SEED_PROJECTS:
                session.add(Project(id=str(uuid.uuid4()), attachments=[], created_at=utcnow(), **p))
        if not session.exec(select(Experience)).first():
            for e in SEED_EXPERIENCE:
                session.add(Experience(id=str(uuid.uuid4()), **e))
        if not session.exec(select(Certification)).first():
            for c in SEED_CERTS:
                session.add(Certification(id=str(uuid.uuid4()), **c))
        if not session.exec(select(ContactMethod)).first():
            for m in SEED_CONTACT_METHODS:
                session.add(ContactMethod(id=str(uuid.uuid4()), **m))
        if not session.exec(select(ContactInfo)).first():
            session.add(ContactInfo(id=str(uuid.uuid4()), tagline=SEED_TAGLINE))
        if not session.exec(select(LandingContent)).first():
            session.add(LandingContent(id=str(uuid.uuid4()), **SEED_LANDING))
        session.commit()


def bootstrap():
    """Create tables, migrate, and seed. Invoked by scripts/bootstrap.py as a
    deploy step — never from a request path, where concurrent cold starts
    would race and double-seed."""
    create_db_and_tables()
    migrate()
    seed_data()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Local dev bootstraps itself for convenience. In the cloud this is a
    # one-shot deploy step, so cold starts stay fast and cannot double-seed.
    if os.getenv("AUTO_BOOTSTRAP", "1") == "1":
        bootstrap()
    yield


app = FastAPI(title="Neel Portfolio API", lifespan=lifespan)

# Comma-separated list, e.g. "https://d111.cloudfront.net,http://localhost:3001".
# The admin runs locally, so its localhost origin stays in the default.
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",") if o.strip()
]

# Registration order is the reverse of execution order: auth runs first and
# rejects unauthorised writes before publish ever sees them.
app.middleware("http")(publish_middleware)
app.middleware("http")(admin_auth_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(experience.router, prefix="/api/experience", tags=["experience"])
app.include_router(certifications.router, prefix="/api/certifications", tags=["certifications"])
app.include_router(education.router, prefix="/api/education", tags=["education"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(contact.router, prefix="/api/contact", tags=["contact"])
app.include_router(about.router, prefix="/api/about", tags=["about"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(landing.router, prefix="/api/landing", tags=["landing"])

# Local development serves uploads off disk. With Supabase storage configured
# the files live in the bucket and this mount would be dead weight on Lambda.
if not storage.using_supabase():
    from fastapi.staticfiles import StaticFiles
    storage.LOCAL_UPLOAD_DIR.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=storage.LOCAL_UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Neel Portfolio API",
        "storage": "supabase" if storage.using_supabase() else "local",
        "auto_rebuild": publish.enabled(),
    }


# AWS Lambda entry point. Imported lazily so local dev does not need mangum.
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:  # pragma: no cover - only missing in a bare local venv
    handler = None
