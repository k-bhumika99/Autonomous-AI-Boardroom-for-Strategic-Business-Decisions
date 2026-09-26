"""Autonomous AI Boardroom — Flask application entry point."""
import logging
import os

from flask import Flask, render_template

from config import Config
from database import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not app.config.get("GEMINI_API_KEY"):
        logging.getLogger("boardroom").warning(
            "\n"
            "==============================================================\n"
            "  GEMINI_API_KEY is NOT set.\n"
            "  Every agent will fail and the agent pages will show an\n"
            "  error instead of analysis.\n"
            "  Fix: get a free key at https://aistudio.google.com/apikey\n"
            "       then put it in your .env file:\n"
            "       GEMINI_API_KEY=your-key-here\n"
            "  Model in use: %s\n"
            "==============================================================",
            app.config.get("GEMINI_MODEL"),
        )

    from auth import auth_bp
    from routes.main_routes import main_bp
    from routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # Jinja helpers used across the dashboards
    from services.formatting import inr, inr_short, compact_number

    app.jinja_env.filters["inr"] = inr
    app.jinja_env.filters["inr_short"] = inr_short
    app.jinja_env.filters["compact"] = compact_number

    # create_all() + additive column migration for older dev databases
    from migrations import ensure_schema
    ensure_schema(app)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
