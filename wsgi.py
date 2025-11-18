"""
WSGI entry point for Flask application.

This module creates the Flask application instance based on the current
environment. For production deployment with Gunicorn, set FLASK_ENV=production.
"""

import os

from app import create_app

# Detect environment (defaults to production for safety)
env = os.environ.get("FLASK_ENV", "production")

# Configuration mapping
config_classes = {
    "development": "app.config.DevelopmentConfig",
    "testing": "app.config.TestingConfig",
    "staging": "app.config.StagingConfig",
    "production": "app.config.ProductionConfig",
}

config_class = config_classes.get(env, "app.config.ProductionConfig")

# Create application instance
app = create_app(config_class)

if __name__ == "__main__":
    app.run()
