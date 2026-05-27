"""EduTrack — Dashboard routes"""

from flask import Blueprint, render_template, g
from ..database import query, get_current_term, get_settings
from .auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    term    = get_current_term()
    settings = get_settings()
    classes = query("SELECT * FROM classes ORDER BY level, department, name")

    stats = {}
    if term:
        stats["total_students"] = query(
            "SELECT COUNT(*) as cnt FROM students WHERE is_active=1", one=True
        )["cnt"]

        stats["scores_entered"] = query(
            """SELECT COUNT(DISTINCT student_id) as cnt FROM scores
               WHERE term_id = ?""", (term["id"],), one=True
        )["cnt"]

        stats["school_average"] = query(
            """SELECT ROUND(AVG(total),1) as avg FROM scores
               WHERE term_id = ?""", (term["id"],), one=True
        )["avg"]

        stats["at_risk"] = query(
            """SELECT COUNT(DISTINCT student_id) as cnt FROM scores
               WHERE term_id = ? AND total < 40""", (term["id"],), one=True
        )["cnt"]

    # Class-level summaries
    class_summaries = []
    for cls in classes:
        student_count = query(
            "SELECT COUNT(*) as cnt FROM students WHERE class_id=? AND is_active=1",
            (cls["id"],), one=True
        )["cnt"]

        avg = None
        if term:
            avg_row = query(
                """SELECT ROUND(AVG(sc.total),1) as avg
                   FROM scores sc
                   JOIN students s ON sc.student_id = s.id
                   WHERE s.class_id = ? AND sc.term_id = ?""",
                (cls["id"], term["id"]), one=True
            )
            avg = avg_row["avg"] if avg_row else None

        class_summaries.append({
            "id":       cls["id"],
            "name":     cls["name"],
            "level":    cls["level"],
            "dept":     cls["department"],
            "students": student_count,
            "average":  avg,
        })

    return render_template("dashboard/index.html",
                           term=term,
                           settings=settings,
                           stats=stats,
                           class_summaries=class_summaries,
                           user=g.user)
