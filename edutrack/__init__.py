"""
EduTrack — School Performance Manager
Flask application factory
"""

import os
from flask import Flask, session, g


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # ── Database path ─────────────────────────────────────────────────────────
    # On Railway: set DATABASE_PATH=/data/edutrack.db (persistent volume)
    # Locally:    falls back to instance/edutrack.db
    db_path = os.environ.get("DATABASE_PATH") or \
              os.path.join(app.instance_path, "edutrack.db")

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-in-production"),
        DATABASE=db_path,
    )

    # Ensure instance folder exists (needed for local fallback)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # ── Initialise database ───────────────────────────────────────────────────
    from .database import init_db, seed_class_subjects
    init_db(app)
    seed_class_subjects(app)

    # ── Load the logged-in user before every request ──────────────────────────
    from .database import query

    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        if user_id:
            g.user = query(
                "SELECT * FROM users WHERE id = ?", (user_id,), one=True
            )
        else:
            g.user = None

    # ── Register blueprints ───────────────────────────────────────────────────
    from .routes.auth      import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.students  import students_bp
    from .routes.scores    import scores_bp
    from .routes.reports   import reports_bp
    from .routes.settings  import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(scores_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    return app
