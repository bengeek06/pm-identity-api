"""
Entry point for development and staging environments.

This module provides the main entry point for running the Flask application
in development and staging environments with appropriate configuration.
"""

import os

from dotenv import load_dotenv

from app import create_app
from app.logger import logger


def main():
    """
    Main entry point for running the Flask application.

    This function detects the environment, loads configuration,
    creates the Flask app, and starts the development server.
    """
    # Detect environment
    env = os.environ.get("FLASK_ENV", "development")

    # Load .env file ONLY if not running in Docker
    # Docker containers have IN_DOCKER_CONTAINER env var or specific variables
    if not os.environ.get("IN_DOCKER_CONTAINER") and not os.environ.get("APP_MODE"):
        env_file = f".env.{env}"
        if os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Loaded environment from {env_file}")
        else:
            logger.warning(f"Environment file {env_file} not found")
    else:
        logger.info("Running in container - using environment variables directly")

    logger.info(f"Running in {env} environment")

    # Configuration mapping
    config_mapping = {
        "production": "app.config.ProductionConfig",
        "staging": "app.config.StagingConfig",
        "testing": "app.config.TestingConfig",
        "development": "app.config.DevelopmentConfig",
    }

    config_class = config_mapping.get(env, "app.config.DevelopmentConfig")
    logger.info(f"Using config class: {config_class}")

    # Create app
    app = create_app(config_class)

    # Development server settings
    debug = env in ["development", "testing"]
    port = int(os.environ.get("PORT", 5000))

    logger.info(f"Starting Flask development server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
