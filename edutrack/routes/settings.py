"""EduTrack — Settings routes"""

from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, g)
from werkzeug.security import generate_password_hash, check_password_hash
from ..database import query, mutate, get_settings
from .auth import login_required, role_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("principal")
def index():
    if request.method == "POST":
        # Save school info keys
        for key in ["school_name", "school_address", "school_phone",
                    "school_email", "current_session", "current_term"]:
            val = request.form.get(key, "").strip()
            if val:
                mutate("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",
                       (key, val))

        # ── Sync current_session & current_term into the proper tables ──
        new_session = request.form.get("current_session", "").strip()
        new_term    = request.form.get("current_term", "").strip()

        if new_session:
            # Ensure session row exists
            existing_sess = query(
                "SELECT id FROM sessions WHERE name=?", (new_session,), one=True
            )
            if not existing_sess:
                mutate("INSERT INTO sessions (name, is_current) VALUES (?,1)",
                       (new_session,))
                sess_id = query(
                    "SELECT id FROM sessions WHERE name=?", (new_session,), one=True
                )["id"]
                for t in ["First Term", "Second Term", "Third Term"]:
                    mutate(
                        "INSERT OR IGNORE INTO terms (session_id,name,is_current) VALUES (?,?,0)",
                        (sess_id, t)
                    )
            else:
                sess_id = existing_sess["id"]

            # Mark this session current, all others not
            mutate("UPDATE sessions SET is_current=0")
            mutate("UPDATE sessions SET is_current=1 WHERE id=?", (sess_id,))

        if new_term and new_session:
            # Mark correct term current
            mutate("UPDATE terms SET is_current=0")
            mutate(
                """UPDATE terms SET is_current=1
                   WHERE name=? AND session_id=(
                       SELECT id FROM sessions WHERE name=?
                   )""",
                (new_term, new_session)
            )

        flash("Settings saved successfully.", "success")
        return redirect(url_for("settings.index"))

    settings = get_settings()
    users    = query(
        "SELECT id, full_name, username, role FROM users ORDER BY role, full_name"
    )
    return render_template("settings/index.html",
                           settings=settings, users=users, user=g.user)


# ── Add user ──────────────────────────────────────────────────────────────────
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


# ── Edit user ─────────────────────────────────────────────────────────────────
@settings_bp.route("/settings/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("principal")
def edit_user(user_id):
    target = query("SELECT * FROM users WHERE id=?", (user_id,), one=True)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("settings.index"))

    error = None
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username  = request.form.get("username", "").strip()
        role      = request.form.get("role", "subject_teacher")

        if not full_name or not username:
            error = "Full name and username are required."
        else:
            clash = query(
                "SELECT id FROM users WHERE username=? AND id!=?",
                (username, user_id), one=True
            )
            if clash:
                error = "That username is already taken."
            else:
                mutate(
                    "UPDATE users SET full_name=?, username=?, role=? WHERE id=?",
                    (full_name, username, role, user_id)
                )
                flash(f"{full_name}'s details updated.", "success")
                return redirect(url_for("settings.index"))

    return render_template("settings/edit_user.html",
                           target=target, error=error, user=g.user)


# ── Change password ───────────────────────────────────────────────────────────
@settings_bp.route("/settings/users/<int:user_id>/password", methods=["GET", "POST"])
@login_required
@role_required("principal")
def change_password(user_id):
    target = query("SELECT * FROM users WHERE id=?", (user_id,), one=True)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("settings.index"))

    error = None
    if request.method == "POST":
        new_pw  = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if len(new_pw) < 6:
            error = "Password must be at least 6 characters."
        elif new_pw != confirm:
            error = "Passwords do not match."
        else:
            mutate(
                "UPDATE users SET password_hash=? WHERE id=?",
                (generate_password_hash(new_pw), user_id)
            )
            flash(f"Password updated for {target['full_name']}.", "success")
            return redirect(url_for("settings.index"))

    return render_template("settings/change_password.html",
                           target=target, error=error, user=g.user)


# ── Delete user ───────────────────────────────────────────────────────────────
@settings_bp.route("/settings/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("principal")
def delete_user(user_id):
    # Prevent deleting yourself
    if user_id == g.user["id"]:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("settings.index"))

    target = query("SELECT full_name FROM users WHERE id=?", (user_id,), one=True)
    if target:
        mutate("DELETE FROM users WHERE id=?", (user_id,))
        flash(f"User {target['full_name']} deleted.", "success")

    return redirect(url_for("settings.index"))
