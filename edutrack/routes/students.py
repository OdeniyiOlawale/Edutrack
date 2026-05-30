"""EduTrack — Students routes"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from ..database import query, mutate, get_current_term, get_grade
from .auth import login_required

students_bp = Blueprint("students", __name__)


def next_student_id():
    last = query("SELECT student_id FROM students ORDER BY id DESC LIMIT 1", one=True)
    if not last:
        return "STU-001"
    try:
        num = int(last["student_id"].split("-")[1]) + 1
    except Exception:
        num = 1
    return f"STU-{num:03d}"


# ── Student list ──────────────────────────────────────────────────────────────
@students_bp.route("/students")
@login_required
def index():
    class_id = request.args.get("class_id", "", type=str)
    search   = request.args.get("q", "").strip()
    classes  = query("SELECT * FROM classes ORDER BY level, name")
    term     = get_current_term()

    # Base query — no window functions for SQLite compatibility
    sql = """
        SELECT s.id, s.student_id, s.full_name, s.gender,
               c.id AS class_id, c.name AS class_name,
               c.level, c.department,
               ROUND(AVG(sc.total), 1) AS avg_score
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN scores sc ON sc.student_id = s.id AND sc.term_id = ?
        WHERE s.is_active = 1
    """
    args = [term["id"] if term else 0]

    if class_id:
        sql += " AND s.class_id = ?"
        args.append(class_id)
    if search:
        sql += " AND (s.full_name LIKE ? OR s.student_id LIKE ?)"
        args += [f"%{search}%", f"%{search}%"]

    sql += " GROUP BY s.id ORDER BY c.name, s.full_name"
    students = query(sql, args)

    return render_template("students/index.html",
                           students=students,
                           classes=classes,
                           selected_class=class_id,
                           search=search,
                           term=term,
                           user=g.user)


# ── Student score sheet ───────────────────────────────────────────────────────
@students_bp.route("/students/<int:student_id>/scores", methods=["GET", "POST"])
@login_required
def student_scores(student_id):
    """
    Show all subjects for a student and allow entering scores
    for each subject in one place.
    """
    term = get_current_term()

    student = query(
        """SELECT s.*, c.name AS class_name, c.level, c.department
           FROM students s JOIN classes c ON s.class_id = c.id
           WHERE s.id = ?""",
        (student_id,), one=True
    )

    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students.index"))

    # All subjects for this student's class, with existing scores
    subjects_scores = query(
        """SELECT sub.id AS subject_id, sub.name AS subject_name,
                  sc.ca1, sc.ca2, sc.ca_total, sc.exam, sc.total
           FROM class_subjects cs
           JOIN subjects sub ON cs.subject_id = sub.id
           LEFT JOIN scores sc
               ON sc.subject_id = sub.id
               AND sc.student_id = ?
               AND sc.term_id    = ?
           WHERE cs.class_id = ?
           ORDER BY cs.sort_order""",
        (student_id, term["id"] if term else 0, student["class_id"])
    )

    # Annotate each row with grade/remark
    rows = []
    for r in subjects_scores:
        grade, remark = get_grade(r["total"])
        rows.append({
            "subject_id":   r["subject_id"],
            "subject_name": r["subject_name"],
            "ca1":          r["ca1"],
            "ca2":          r["ca2"],
            "ca_total":     r["ca_total"],
            "exam":         r["exam"],
            "total":        r["total"],
            "grade":        grade,
            "remark":       remark,
        })

    # Summary stats
    scored = [r for r in rows if r["total"] is not None]
    summary = None
    if scored:
        total_score = sum(r["total"] for r in scored)
        average     = round(total_score / len(scored), 1)
        grade, remark = get_grade(average)
        summary = {
            "total_score": total_score,
            "average":     average,
            "grade":       grade,
            "remark":      remark,
            "entered":     len(scored),
            "total_subj":  len(rows),
        }

    return render_template(
        "students/scores.html",
        student=student,
        rows=rows,
        summary=summary,
        term=term,
        user=g.user,
    )


# ── Add student ───────────────────────────────────────────────────────────────
@students_bp.route("/students/add", methods=["GET", "POST"])
@login_required
def add():
    classes = query("SELECT * FROM classes ORDER BY level, name")
    error   = None

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        gender    = request.form.get("gender")
        class_id  = request.form.get("class_id")
        dob       = request.form.get("date_of_birth") or None

        if not full_name or not class_id:
            error = "Full name and class are required."
        else:
            sid = next_student_id()
            mutate(
                """INSERT INTO students (student_id, full_name, gender, date_of_birth, class_id)
                   VALUES (?,?,?,?,?)""",
                (sid, full_name, gender, dob, class_id)
            )
            flash(f"Student {full_name} added ({sid}).", "success")
            return redirect(url_for("students.index"))

    return render_template("students/add.html",
                           classes=classes, error=error, user=g.user)


# ── Edit student ──────────────────────────────────────────────────────────────
@students_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit(student_id):
    student = query("SELECT * FROM students WHERE id=?", (student_id,), one=True)
    classes = query("SELECT * FROM classes ORDER BY level, name")
    error   = None

    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        gender    = request.form.get("gender")
        class_id  = request.form.get("class_id")
        dob       = request.form.get("date_of_birth") or None

        if not full_name or not class_id:
            error = "Full name and class are required."
        else:
            mutate(
                """UPDATE students SET full_name=?, gender=?, class_id=?,
                   date_of_birth=? WHERE id=?""",
                (full_name, gender, class_id, dob, student_id)
            )
            flash("Student updated.", "success")
            return redirect(url_for("students.index",
                                    class_id=student["class_id"]))

    return render_template("students/edit.html",
                           student=student, classes=classes,
                           error=error, user=g.user)
