"""
EduTrack — Database layer
Handles connection, initialisation, and seeding.
"""

import sqlite3
import os
import click
from flask import g


def get_db(app=None):
    """Return a database connection, reusing within request context."""
    from flask import current_app
    _app = app or current_app

    if "db" not in g:
        g.db = sqlite3.connect(
            _app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables from schema.sql."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    # Also check same directory
    if not os.path.exists(schema_path):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")

        with open(schema_path, "r") as f:
            db.executescript(f.read())
        db.commit()
        db.close()

    app.teardown_appcontext(close_db)


def seed_class_subjects(app):
    """
    Seed the class_subjects mapping table.
    JSS 1-3 → 15 JSS subjects
    SS departments → 9 department-specific subjects
    """
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

    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")

        classes = db.execute("SELECT id, name, level, department FROM classes").fetchall()

        for cls in classes:
            # Skip if already seeded
            existing = db.execute(
                "SELECT COUNT(*) as cnt FROM class_subjects WHERE class_id = ?",
                (cls["id"],)
            ).fetchone()["cnt"]

            if existing > 0:
                continue

            if cls["level"] == "JSS":
                subject_list = JSS_SUBJECTS
            else:
                subject_list = SS_SUBJECTS.get(cls["department"], [])

            for order, subj_name in enumerate(subject_list):
                subj = db.execute(
                    "SELECT id FROM subjects WHERE name = ?", (subj_name,)
                ).fetchone()
                if subj:
                    db.execute(
                        "INSERT OR IGNORE INTO class_subjects (class_id, subject_id, sort_order) VALUES (?,?,?)",
                        (cls["id"], subj["id"], order)
                    )

        db.commit()
        db.close()


# ── Query helpers ─────────────────────────────────────────────────────────────

def query(sql, args=(), one=False):
    """Run a SELECT and return Row(s)."""
    from flask import current_app
    db = get_db()
    cur = db.execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def mutate(sql, args=()):
    """Run INSERT / UPDATE / DELETE and commit."""
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def get_current_term():
    """Return the current term row."""
    return query(
        """SELECT t.id, t.name, s.name AS session_name
           FROM terms t
           JOIN sessions s ON t.session_id = s.id
           WHERE t.is_current = 1
           LIMIT 1""",
        one=True,
    )


def get_settings():
    """Return settings as a plain dict."""
    rows = query("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


def get_grade(total):
    """Return (grade, remark) for a numeric total."""
    if total is None:
        return ("—", "—")
    if total >= 70: return ("A", "Excellent")
    if total >= 60: return ("B", "Good")
    if total >= 50: return ("C", "Average")
    if total >= 40: return ("D", "Below Average")
    return ("F", "Fail")
