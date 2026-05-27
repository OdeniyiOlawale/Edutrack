"""EduTrack — Reports routes"""

from flask import Blueprint, render_template, request, g
from ..database import query, get_current_term, get_settings, get_grade
from .auth import login_required

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports/card")
@login_required
def report_card():
    classes    = query("SELECT * FROM classes ORDER BY level, name")
    term       = get_current_term()
    settings   = get_settings()
    class_id   = request.args.get("class_id", "", type=str)
    student_id = request.args.get("student_id", "", type=str)

    students = []
    if class_id:
        students = query(
            "SELECT * FROM students WHERE class_id=? AND is_active=1 ORDER BY full_name",
            (class_id,)
        )

    report = None
    if student_id and term:
        student = query(
            """SELECT s.*, c.name AS class_name, c.level, c.department
               FROM students s JOIN classes c ON s.class_id=c.id
               WHERE s.id=?""", (student_id,), one=True
        )
        if student:
            scores = query(
                """SELECT sub.name AS subject, sc.ca1, sc.ca2, sc.ca_total,
                          sc.exam, sc.total
                   FROM scores sc
                   JOIN subjects sub ON sc.subject_id = sub.id
                   JOIN class_subjects cs ON cs.subject_id = sub.id
                                         AND cs.class_id = ?
                   WHERE sc.student_id=? AND sc.term_id=?
                   ORDER BY cs.sort_order""",
                (student["class_id"], student_id, term["id"])
            )

            # Class position
            pos_row = query(
                """WITH ranked AS (
                       SELECT student_id,
                              RANK() OVER (ORDER BY AVG(total) DESC) AS pos
                       FROM scores WHERE term_id=?
                       GROUP BY student_id
                   )
                   SELECT pos FROM ranked WHERE student_id=?""",
                (term["id"], student_id), one=True
            )

            # Class size
            class_size = query(
                "SELECT COUNT(*) as cnt FROM students WHERE class_id=? AND is_active=1",
                (student["class_id"],), one=True
            )["cnt"]

            # Totals
            total_score = sum(r["total"] or 0 for r in scores)
            n_subjects  = len(scores)
            average     = round(total_score / n_subjects, 1) if n_subjects else 0
            grade, remark = get_grade(average)

            report = {
                "student":     student,
                "scores":      scores,
                "total_score": total_score,
                "average":     average,
                "grade":       grade,
                "remark":      remark,
                "position":    pos_row["pos"] if pos_row else "—",
                "class_size":  class_size,
                "get_grade":   get_grade,
            }

    return render_template("reports/card.html",
                           classes=classes,
                           students=students,
                           selected_class=class_id,
                           selected_student=student_id,
                           report=report,
                           term=term,
                           settings=settings,
                           user=g.user)


@reports_bp.route("/reports/summary")
@login_required
def summary():
    term    = get_current_term()
    classes = query("SELECT * FROM classes ORDER BY level, name")

    summaries = []
    for cls in classes:
        students = query(
            "SELECT id FROM students WHERE class_id=? AND is_active=1", (cls["id"],)
        )
        if not students or not term:
            summaries.append({"class": cls, "data": None})
            continue

        student_ids = [s["id"] for s in students]
        placeholders = ",".join("?" * len(student_ids))

        avg_row = query(
            f"""SELECT ROUND(AVG(total),1) as avg,
                       ROUND(MAX(total),1) as high,
                       ROUND(MIN(total),1) as low,
                       COUNT(DISTINCT student_id) as entered
                FROM scores
                WHERE term_id=? AND student_id IN ({placeholders})""",
            [term["id"]] + student_ids, one=True
        )

        pass_count = query(
            f"""SELECT COUNT(DISTINCT student_id) as cnt FROM scores
                WHERE term_id=? AND total>=40 AND student_id IN ({placeholders})""",
            [term["id"]] + student_ids, one=True
        )["cnt"]

        summaries.append({
            "class":      cls,
            "students":   len(students),
            "average":    avg_row["avg"],
            "highest":    avg_row["high"],
            "lowest":     avg_row["low"],
            "entered":    avg_row["entered"],
            "pass_rate":  round(100 * pass_count / len(students), 1) if students else 0,
        })

    return render_template("reports/summary.html",
                           summaries=summaries, term=term, user=g.user)
