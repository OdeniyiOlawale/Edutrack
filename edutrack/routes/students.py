"""EduTrack — Students routes"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from ..database import query, mutate, get_current_term
from .auth import login_required

students_bp = Blueprint("students", __name__)


def next_student_id(class_id):
    """Generate next sequential student ID like STU-001."""
    last = query(
        "SELECT student_id FROM students ORDER BY id DESC LIMIT 1", one=True
    )
    if not last:
        return "STU-001"
    try:
        num = int(last["student_id"].split("-")[1]) + 1
    except Exception:
        num = 1
    return f"STU-{num:03d}"


@students_bp.route("/students")
@login_required
def index():
    class_id   = request.args.get("class_id", "", type=str)
    search     = request.args.get("q", "").strip()
    classes    = query("SELECT * FROM classes ORDER BY level, name")
    term       = get_current_term()

    sql = """
        SELECT s.*, c.name AS class_name, c.level, c.department,
               ROUND(AVG(sc.total), 1) AS avg_score,
               RANK() OVER (PARTITION BY s.class_id ORDER BY AVG(sc.total) DESC) AS position
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
            sid = next_student_id(class_id)
            mutate(
                """INSERT INTO students (student_id, full_name, gender, date_of_birth, class_id)
                   VALUES (?,?,?,?,?)""",
                (sid, full_name, gender, dob, class_id)
            )
            flash(f"Student {full_name} added successfully ({sid}).", "success")
            return redirect(url_for("students.index"))

    return render_template("students/add.html",
                           classes=classes, error=error, user=g.user)


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
            return redirect(url_for("students.index"))

    return render_template("students/edit.html",
                           student=student, classes=classes,
                           error=error, user=g.user)
