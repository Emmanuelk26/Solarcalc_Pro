"""
SolarCalc Pro — Flask Application Entry Point
"""

from flask import Flask
from config import config


def create_app(env: str = "default") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config[env])

    # Register blueprints
    from routes.calculators import bp
    app.register_blueprint(bp)

    return app


if __name__ == "__main__":
    app = create_app("development")
    app.run(debug=True, host="0.0.0.0", port=5000)
