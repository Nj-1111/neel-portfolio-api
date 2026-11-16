"""One-shot deploy step: create tables, migrate, seed.

Run against the target database before/after deploying the API:

    DATABASE_URL='postgresql+psycopg://...' python scripts/bootstrap.py

Safe to run repeatedly — table creation is IF NOT EXISTS, the migration is
idempotent, and seeding only inserts when a table is empty.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import DATABASE_URL  # noqa: E402
from app.main import bootstrap  # noqa: E402

if __name__ == "__main__":
    target = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"bootstrapping: {target}")
    bootstrap()
    print("done — tables created, migrated and seeded")
