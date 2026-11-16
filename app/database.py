import os
import json
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neel_portfolio.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Lambda + Supabase: every warm container would otherwise hold its own
    # pool and exhaust the database's connection limit. NullPool hands the
    # connection back immediately and lets Supabase's transaction-mode pooler
    # (port 6543) do the pooling. That pooler also cannot replay prepared
    # statements, hence prepare_threshold=None for psycopg3.
    connect_args = {}
    if DATABASE_URL.startswith("postgresql+psycopg://"):
        connect_args["prepare_threshold"] = None
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def _table_names(conn) -> set[str]:
    rows = conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def _columns(conn, table: str) -> set[str]:
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def migrate():
    """Reshape pre-existing SQLite tables to the current models, preserving data.

    SQLModel.create_all only creates missing tables, it never alters existing
    ones. This fills that gap for the admin-mockup schema change. Runs on every
    boot and is a no-op once the columns are in place.

    ponytail: hand-rolled for SQLite because this is the only schema change in
    the project's life so far. Bring in Alembic if a second one shows up.
    """
    if not IS_SQLITE:
        return

    with engine.begin() as conn:
        tables = _table_names(conn)

        # --- experience: period kept, + location/highlights, - description/tags
        if "experience" in tables:
            cols = _columns(conn, "experience")
            if "location" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE experience ADD COLUMN location VARCHAR DEFAULT ''"
                )
            if "highlights" not in cols:
                conn.exec_driver_sql("ALTER TABLE experience ADD COLUMN highlights JSON")
                # fold the old single description/tags pair into one highlight
                if "description" in cols:
                    rows = conn.exec_driver_sql(
                        "SELECT id, role, description, tags FROM experience"
                    ).fetchall()
                    for row_id, role, description, tags in rows:
                        if not description and not tags:
                            continue
                        try:
                            tag_list = json.loads(tags) if tags else []
                        except (TypeError, ValueError):
                            tag_list = []
                        # title stays empty: the old shape had no per-highlight
                        # title, and echoing the role here renders it twice
                        highlight = [{
                            "title": "",
                            "desc": description or "",
                            "tags": tag_list,
                        }]
                        conn.exec_driver_sql(
                            "UPDATE experience SET highlights = ? WHERE id = ?",
                            (json.dumps(highlight), row_id),
                        )
            for dead in ("description", "tags"):
                if dead in _columns(conn, "experience"):
                    conn.exec_driver_sql(f"ALTER TABLE experience DROP COLUMN {dead}")

        # --- certification: + badge/credential_id, - issuer/issued/expires/link
        if "certification" in tables:
            cols = _columns(conn, "certification")
            if "badge" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE certification ADD COLUMN badge VARCHAR DEFAULT ''"
                )
                if "issuer" in cols:
                    # issuer is the closest thing the old shape had to a badge
                    conn.exec_driver_sql(
                        "UPDATE certification SET badge = COALESCE(issuer, '')"
                    )
            if "credential_id" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE certification ADD COLUMN credential_id VARCHAR DEFAULT ''"
                )
                if "link" in cols:
                    conn.exec_driver_sql(
                        "UPDATE certification SET credential_id = COALESCE(link, '')"
                    )
            for dead in ("issuer", "issued", "expires", "link"):
                if dead in _columns(conn, "certification"):
                    conn.exec_driver_sql(f"ALTER TABLE certification DROP COLUMN {dead}")

        # --- resume_file: + content
        if "resume_file" in tables and "content" not in _columns(conn, "resume_file"):
            conn.exec_driver_sql(
                "ALTER TABLE resume_file ADD COLUMN content VARCHAR DEFAULT ''"
            )

        # --- about_article: + slug, so one table holds both the "site" and
        #     "me" articles. The pre-existing row is the site one.
        if "about_article" in tables and "slug" not in _columns(conn, "about_article"):
            conn.exec_driver_sql(
                "ALTER TABLE about_article ADD COLUMN slug VARCHAR DEFAULT 'site'"
            )
            conn.exec_driver_sql(
                "UPDATE about_article SET slug = 'site' WHERE slug IS NULL OR slug = ''"
            )


def get_session():
    with Session(engine) as session:
        yield session
