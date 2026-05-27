"""EduTrack — Scores routes"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, g, jsonify)
from ..database import query, mutate, get_current_term, get_grade
from .auth import login_required

scores_bp = Blueprint("scores", __name__)


@scores_bp.route("/scores")
@login_required
def index():
    classes  = query("SELECT * FROM classes ORDER BY level, name")
    term     = get_current_term()
    class_id = request.args.get("class_id", "", type=str)
    subj_id  = request.args.get("subject_id", "", type=str)

    subjects = []
    students_scores = []

    if class_id:
        subjects = query(
            """SELECT s.id, s.name FROM subjects s
               JOIN class_subjects cs ON cs.subject_id = s.id
               WHERE cs.class_id = ?
               ORDER BY cs.sort_order""",
            (class_id,)
        )

    if class_id and subj_id and term:
        students_scores = query(
            """SELECT st.id, st.student_id AS code, st.full_name,
                      sc.ca1, sc.ca2, sc.ca_total, sc.exam, sc.total
               FROM students st
               LEFT JOIN scores sc
                   ON sc.student_id = st.id
                   AND sc.subject_id = ?
                   AND sc.term_id    = ?
               WHERE st.class_id = ? AND st.is_active = 1
               ORDER BY st.full_name""",
            (subj_id, term["id"], class_id)
        )

    # Summary stats for the current selection
    summary = None
    if students_scores and subj_id and term:
        totals = [r["total"] for r in students_scores if r["total"] is not None]
        if totals:
            summary = {
                "average": round(sum(totals) / len(totals), 1),
                "highest": max(totals),
                "lowest":  min(totals),
                "entered": len(totals),
                "total":   len(students_scores),
            }

    return render_template("scores/index.html",
                           classes=classes,
                           subjects=subjects,
                           students_scores=students_scores,
                           selected_class=class_id,
                           selected_subject=subj_id,
                           term=term,
                           summary=summary,
                           get_grade=get_grade,
                           user=g.user)


@scores_bp.route("/scores/save", methods=["POST"])
@login_required
def save():
    """
    Receive JSON payload and bulk-save scores.
    Payload: { term_id, subject_id, scores: [{student_id, ca1, ca2, exam}] }
    """
    data       = request.get_json()
    term_id    = data.get("term_id")
    subject_id = data.get("subject_id")
    rows       = data.get("scores", [])

    if not term_id or not subject_id:
        return jsonify({"ok": False, "error": "Missing term or subject"}), 400

    saved = 0
    errors = []
    for row in rows:
        sid  = row.get("student_id")
        ca1  = row.get("ca1")
        ca2  = row.get("ca2")
        exam = row.get("exam")

        # Validate ranges
        try:
            if ca1  is not None and not (0 <= float(ca1)  <= 20): raise ValueError
            if ca2  is not None and not (0 <= float(ca2)  <= 20): raise ValueError
            if exam is not None and not (0 <= float(exam) <= 60): raise ValueError
        except (ValueError, TypeError):
            errors.append(f"Invalid score for student {sid}")
            continue

        mutate(
            """INSERT INTO scores (student_id, subject_id, term_id, ca1, ca2, exam, updated_at)
               VALUES (?,?,?,?,?,?, CURRENT_TIMESTAMP)
               ON CONFLICT(student_id, subject_id, term_id)
               DO UPDATE SET ca1=excluded.ca1, ca2=excluded.ca2,
                             exam=excluded.exam,
                             updated_at=CURRENT_TIMESTAMP""",
            (sid, subject_id, term_id,
             float(ca1) if ca1 not in (None, "") else None,
             float(ca2) if ca2 not in (None, "") else None,
             float(exam) if exam not in (None, "") else None)
        )
        saved += 1

    return jsonify({"ok": True, "saved": saved, "errors": errors})
