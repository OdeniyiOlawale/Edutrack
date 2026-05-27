"""EduTrack — Settings routes"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash
from ..database import query, mutate, get_settings
from .auth import login_required, role_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("principal")
def index():
    if request.method == "POST":
        for key in ["school_name", "school_address", "school_phone",
                    "current_session", "current_term"]:
            val = request.form.get(key, "").strip()
            if val:
                mutate("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",
                       (key, val))
        flash("Settings saved.", "success")
        return redirect(url_for("settings.index"))

    settings = get_settings()
    users    = query("SELECT id, full_name, username, role FROM users ORDER BY role, full_name")
    return render_template("settings/index.html",
                           settings=settings, users=users, user=g.user)


@settings_bp.route("/settings/users/add", methods=["POST"])
@login_required
@role_required("principal")
def add_user():
    full_name = request.form.get("full_name", "").strip()
    username  = request.form.get("username", "").strip()
    password  = request.form.get("password", "")
    role      = request.form.get("role", "subject_teacher")

    if not full_name or not username or not password:
        flash("All fields are required.", "error")
    elif len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
    else:
        existing = query("SELECT id FROM users WHERE username=?", (username,), one=True)
        if existing:
            flash("Username already taken.", "error")
        else:
            mutate(
                """INSERT INTO users (full_name, username, password_hash, role)
                   VALUES (?,?,?,?)""",
                (full_name, username, generate_password_hash(password), role)
            )
            flash(f"User {full_name} added.", "success")

    return redirect(url_for("settings.index"))
