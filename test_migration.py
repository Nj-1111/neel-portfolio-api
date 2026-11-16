"""Check that migrate() reshapes an old-schema DB without losing data.

Run:  ./venv/bin/python test_migration.py
"""
import json
import os
import sqlite3
import tempfile


def build_old_db(path: str) -> None:
    """Recreate the pre-mockup schema and a row in each changed table."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE experience (
            id VARCHAR PRIMARY KEY, role VARCHAR, company VARCHAR, period VARCHAR,
            description VARCHAR, tags JSON, pinned BOOLEAN, sort_order INTEGER
        );
        CREATE TABLE certification (
            id VARCHAR PRIMARY KEY, name VARCHAR, issuer VARCHAR, issued VARCHAR,
            expires VARCHAR, link VARCHAR, sort_order INTEGER
        );
        CREATE TABLE resume_file (
            id VARCHAR PRIMARY KEY, file_url VARCHAR, updated_at DATETIME
        );
    """)
    conn.execute(
        "INSERT INTO experience VALUES (?,?,?,?,?,?,?,?)",
        ("x1", "Intern", "ACME", "2026", "Did the thing.", json.dumps(["AWS", "Python"]), 1, 1),
    )
    conn.execute(
        "INSERT INTO certification VALUES (?,?,?,?,?,?,?)",
        ("c1", "AWS CP", "Amazon Web Services", "2024", "", "https://verify/abc", 1),
    )
    conn.execute("INSERT INTO resume_file VALUES (?,?,?)", ("r1", "/uploads/cv.pdf", "2026-01-01"))
    conn.commit()
    conn.close()


def columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def main() -> None:
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "old.db")
    build_old_db(db)

    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    from app.database import migrate, create_db_and_tables

    create_db_and_tables()
    migrate()
    migrate()  # must be safe to run on every boot

    conn = sqlite3.connect(db)

    exp_cols = columns(conn, "experience")
    assert "location" in exp_cols, exp_cols
    assert "highlights" in exp_cols, exp_cols
    assert "description" not in exp_cols, "old description column should be gone"
    assert "tags" not in exp_cols, "old tags column should be gone"

    role, highlights = conn.execute("SELECT role, highlights FROM experience").fetchone()
    assert role == "Intern", role
    hl = json.loads(highlights)
    assert len(hl) == 1, hl
    assert hl[0]["desc"] == "Did the thing.", hl
    assert hl[0]["tags"] == ["AWS", "Python"], hl
    assert hl[0]["title"] == "", "title must stay empty so the role is not echoed twice"

    cert_cols = columns(conn, "certification")
    assert "badge" in cert_cols and "credential_id" in cert_cols, cert_cols
    for dead in ("issuer", "issued", "expires", "link"):
        assert dead not in cert_cols, f"{dead} should be gone"

    name, badge, cred = conn.execute(
        "SELECT name, badge, credential_id FROM certification"
    ).fetchone()
    assert name == "AWS CP", name
    assert badge == "Amazon Web Services", badge
    assert cred == "https://verify/abc", cred

    assert "content" in columns(conn, "resume_file")
    file_url, content = conn.execute("SELECT file_url, content FROM resume_file").fetchone()
    assert file_url == "/uploads/cv.pdf", file_url
    assert content in ("", None), content

    conn.close()
    print("migration ok: columns reshaped, data preserved, idempotent")


if __name__ == "__main__":
    main()
