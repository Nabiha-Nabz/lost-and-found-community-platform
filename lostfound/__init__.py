from pathlib import Path

from flask import Flask, render_template

from config import Config
from .extensions import csrf, db, login_manager
from .models import User
from .seed import seed_database


def create_app(config_object=Config):
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config.from_object(config_object)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/error.html", code=403, title="Access denied", message="You do not have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/error.html", code=404, title="Page not found", message="The page may have moved or no longer exists."), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("errors/error.html", code=413, title="Upload too large", message="Please upload images with a combined size below 8 MB."), 413

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/error.html", code=500, title="Something went wrong", message="The request could not be completed. Please try again."), 500

    with app.app_context():
        db.create_all()
        if not app.config.get("TESTING"):
            seed_database()

    return app
