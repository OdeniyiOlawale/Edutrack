"""
EduTrack — Authentication routes
Login / logout / session management
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, g)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from ..database import query, mutate, get_db

auth_bp = Blueprint("auth", __name__)


# ── Decorators ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login"))
            user = query("SELECT role FROM users WHERE id = ?",
                         (session["user_id"],), one=True)
            if not user or user["role"] not in roles:
                flash("You don't have permission to access that page.", "error")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator


def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id:
        g.user = query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    else:
        g.user = None


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.before_app_request
def before_request():
    load_logged_in_user()


@auth_bp.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = query("SELECT * FROM users WHERE username = ?",
                     (username,), one=True)

        if not user:
            error = "Username not found."
        elif not check_password_hash(user["password_hash"], password):
            error = "Incorrect password."
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_role"] = user["role"]
            return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    """
    First-time setup: create the principal account.
    Only works if no users exist yet.
    """
    existing = query("SELECT COUNT(*) as cnt FROM users", one=True)
    if existing and existing["cnt"] > 0:
        flash("Setup already complete. Please log in.", "info")
        return redirect(url_for("auth.login"))

    error = None
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username  = request.form.get("username", "").strip()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        if not full_name or not username or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            mutate(
                """INSERT INTO users (full_name, username, password_hash, role)
                   VALUES (?, ?, ?, 'principal')""",
                (full_name, username, generate_password_hash(password))
            )
            flash("Principal account created. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/setup.html", error=error)
