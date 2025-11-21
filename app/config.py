# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
config.py
---------

This module defines configuration classes for the Flask application based on
the environment.

Classes:
    - Config: Base configuration common to all environments.
    - DevelopmentConfig: Configuration for development.
    - TestingConfig: Configuration for testing.
    - StagingConfig: Configuration for staging.
    - ProductionConfig: Configuration for production.

Each class defines main parameters such as the secret key, database URL,
debug mode, and SQLAlchemy modification tracking.
"""

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file ONLY if not running in Docker
# This hook ensures environment variables are loaded for flask commands
if not os.environ.get("IN_DOCKER_CONTAINER") and not os.environ.get(
    "APP_MODE"
):
    env = os.environ.get("FLASK_ENV", "development")
    ENV_FILE = f".env.{env}"
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
    # Fallback to generic .env if environment-specific file doesn't exist
    elif os.path.exists(".env"):
        load_dotenv(".env")


class Config:
    """
    Base configuration common to all environments.

    Attributes:
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Disable SQLAlchemy event system.
        MAX_CONTENT_LENGTH (int): Maximum allowed request size in bytes (16 MB).
        USE_STORAGE_SERVICE (bool): Enable/disable Storage Service integration.
    """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Allow uploads up to 16 MB (enough for avatar images)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Validate critical environment variables
    JWT_SECRET = os.environ.get("JWT_SECRET")
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set.")

    FLASK_ENV = os.environ.get("FLASK_ENV")
    if not FLASK_ENV:
        raise ValueError("FLASK_ENV environment variable is not set.")

    use_storage_env = os.environ.get("USE_STORAGE_SERVICE")
    if use_storage_env is None:
        USE_STORAGE_SERVICE = False
    else:
        USE_STORAGE_SERVICE = use_storage_env.lower() in ("true", "yes", "1")

    if USE_STORAGE_SERVICE:
        # Storage Service URL (validated at startup if USE_STORAGE_SERVICE=True)
        STORAGE_SERVICE_URL = os.environ.get("STORAGE_SERVICE_URL")
        if not STORAGE_SERVICE_URL:
            error_msg = (
                "Configuration Error: USE_GUARDIAN_SERVICE is enabled (true) "
                "but GUARDIAN_SERVICE_URL environment variable is not set. "
                "Either set GUARDIAN_SERVICE_URL to a valid URL or disable "
                "Guardian Service integration by setting USE_GUARDIAN_SERVICE=false"
            )
            logger.error(error_msg)
            logger.error(
                "Current environment variables: "
                "USE_GUARDIAN_SERVICE=%s, GUARDIAN_SERVICE_URL=%s",
                os.environ.get("USE_GUARDIAN_SERVICE", "not set"),
                os.environ.get("GUARDIAN_SERVICE_URL", "not set"),
            )
            raise ValueError(
                "STORAGE_SERVICE_URL environment variable is not set "
                "while USE_STORAGE_SERVICE is enabled."
            )
        STORAGE_REQUEST_TIMEOUT = int(
            os.environ.get("STORAGE_REQUEST_TIMEOUT", "30")
        )

        # Maximum avatar file size in MB
        MAX_AVATAR_SIZE_MB = int(os.environ.get("MAX_AVATAR_SIZE_MB", "5"))

        # Guardian Service integration toggle
        use_guardian_env = os.environ.get("USE_GUARDIAN_SERVICE", "true")
        if use_guardian_env is None:
            USE_GUARDIAN_SERVICE = False
        else:
            USE_GUARDIAN_SERVICE = use_guardian_env.lower() in (
                "true",
                "yes",
                "1",
            )

        if USE_GUARDIAN_SERVICE:
            # Guardian Service URL (validated at startup if USE_GUARDIAN_SERVICE=True)
            GUARDIAN_SERVICE_URL = os.environ.get("GUARDIAN_SERVICE_URL")
            if not GUARDIAN_SERVICE_URL:
                error_msg = (
                    "Configuration Error: USE_GUARDIAN_SERVICE is enabled (true) "
                    "but GUARDIAN_SERVICE_URL environment variable is not set. "
                    "Either set GUARDIAN_SERVICE_URL to a valid URL or disable "
                    "Guardian Service integration by setting USE_GUARDIAN_SERVICE=false"
                )
                logger.error(error_msg)
                logger.error(
                    "Current environment variables: "
                    "USE_GUARDIAN_SERVICE=%s, GUARDIAN_SERVICE_URL=%s",
                    os.environ.get("USE_GUARDIAN_SERVICE", "not set"),
                    os.environ.get("GUARDIAN_SERVICE_URL", "not set"),
                )
                raise ValueError(
                    "GUARDIAN_SERVICE_URL environment variable is not set "
                    "while USE_GUARDIAN_SERVICE is enabled."
                )

        GUARDIAN_SERVICE_TIMEOUT = float(
            os.environ.get("GUARDIAN_SERVICE_TIMEOUT", "5")
        )


class DevelopmentConfig(Config):
    """
    Configuration for the development environment.

    Attributes:
        DEBUG (bool): Enable debug mode.
        SQLALCHEMY_DATABASE_URI (str): Database URI for development.
    """

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    @classmethod
    def validate_config(cls):
        """Validate development configuration."""
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable is not set.")


class TestingConfig(Config):
    """
    Configuration for the testing environment.

    Attributes:
        TESTING (bool): Enable testing mode.
        SQLALCHEMY_DATABASE_URI (str): Database URI for testing.
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    @classmethod
    def validate_config(cls):
        """Validate testing configuration."""
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable is not set.")


class StagingConfig(Config):
    """
    Configuration for the staging environment.

    Attributes:
        DEBUG (bool): Enable debug mode.
        SQLALCHEMY_DATABASE_URI (str): Database URI for staging.
    """

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    @classmethod
    def validate_config(cls):
        """Validate staging configuration."""
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable is not set.")


class ProductionConfig(Config):
    """
    Configuration for the production environment.

    Attributes:
        DEBUG (bool): Disable debug mode.
        SQLALCHEMY_DATABASE_URI (str): Database URI for production.
    """

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    @classmethod
    def validate_config(cls):
        """Validate production configuration."""
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable is not set.")
