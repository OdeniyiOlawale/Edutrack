"""
EduTrack — Database layer
Handles connection, initialisation, and seeding.
"""

import sqlite3
import os
from flask import g


# ── Schema path — resolved relative to this file, always reliable ─────────────
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_db():
    """Return a DB connection, reused within the current request context."""
    from flask import current_app
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _raw_connect(db_path):
    """Open a direct connection outside of request context (for startup)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(app):
    """Create all tables from schema.sql. Safe to call multiple times."""
    if not os.path.exists(SCHEMA_PATH):
        raise RuntimeError(f"schema.sql not found at {SCHEMA_PATH}")

    db_path = app.config["DATABASE"]

    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = _raw_connect(db_path)
    try:
        with open(SCHEMA_PATH, "r") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()

    app.teardown_appcontext(close_db)


def seed_class_subjects(app):
    """Seed class→subject mappings. Skips classes already seeded."""
    JSS_SUBJECTS = [
        "Mathematics", "English Language", "Basic Science", "Social Studies",
        "Civic Education", "Agricultural Science", "Home Economics",
        "Computer Studies", "French", "Christian/Islamic Religious Studies",
        "Physical & Health Education", "Fine Arts", "Music",
        "Business Studies", "Yoruba/Hausa/Igbo Language",
    ]
    SS_SUBJECTS = {
        "Science":    ["Mathematics", "English Language", "Physics", "Chemistry",
                       "Biology", "Further Mathematics", "Geography",
                       "Computer Studies", "Agricultural Science"],
        "Arts":       ["Mathematics", "English Language", "Literature in English",
                       "Government", "Christian/Islamic Religious Studies", "History",
                       "French", "Fine Arts", "Music"],
        "Commercial": ["Mathematics", "English Language", "Economics", "Commerce",
                       "Accounting", "Civic Education", "Computer Studies",
                       "Office Practice", "Marketing"],
    }

    db_path = app.config["DATABASE"]
    conn = _raw_connect(db_path)
    try:
        classes = conn.execute(
            "SELECT id, name, level, department FROM classes"
        ).fetchall()

        for cls in classes:
            existing = conn.execute(
                "SELECT COUNT(*) AS cnt FROM class_subjects WHERE class_id=?",
                (cls["id"],)
            ).fetchone()["cnt"]

            if existing > 0:
                continue

            subject_list = (
                JSS_SUBJECTS if cls["level"] == "JSS"
                else SS_SUBJECTS.get(cls["department"], [])
            )

            for order, name in enumerate(subject_list):
                subj = conn.execute(
                    "SELECT id FROM subjects WHERE name=?", (name,)
                ).fetchone()
                if subj:
                    conn.execute(
                        """INSERT OR IGNORE INTO class_subjects
                           (class_id, subject_id, sort_order) VALUES (?,?,?)""",
                        (cls["id"], subj["id"], order)
                    )
        conn.commit()
    finally:
        conn.close()


# ── Request-scoped query helpers ──────────────────────────────────────────────

def query(sql, args=(), one=False):
    """Run a SELECT within the current request context."""
    cur = get_db().execute(sql, args)
    rv  = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def mutate(sql, args=()):
    """Run INSERT / UPDATE / DELETE and commit."""
    db  = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def get_current_term():
    return query(
        """SELECT t.id, t.name, s.name AS session_name
           FROM terms t
           JOIN sessions s ON t.session_id = s.id
           WHERE t.is_current = 1
           LIMIT 1""",
        one=True,
    )


def get_settings():
    rows = query("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


def get_grade(total):
    if total is None:       return ("—", "—")
    if total >= 70:         return ("A", "Excellent")
    if total >= 60:         return ("B", "Good")
    if total >= 50:         return ("C", "Average")
    if total >= 40:         return ("D", "Below Average")
    return ("F", "Fail")
