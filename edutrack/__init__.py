"""
EduTrack — School Performance Manager
Flask application entry point and configuration
"""

import os
from flask import Flask
from .database import init_db, seed_class_subjects


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # DATABASE: use /data volume on Railway (persistent), fallback to instance/
    db_path = os.environ.get("DATABASE_PATH") or \
              os.path.join(app.instance_path, "edutrack.db")

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-in-production"),
        DATABASE=db_path,
    )

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialise DB
    with app.app_context():
        init_db(app)
        seed_class_subjects(app)

    # Register blueprints
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
