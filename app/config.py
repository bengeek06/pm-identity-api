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

logger = logging.getLogger(__name__)


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

    # Storage Service integration toggle
    # Set to False to run Identity Service autonomously without Storage Service
    USE_STORAGE_SERVICE = os.environ.get(
        "USE_STORAGE_SERVICE", "true"
    ).lower() in (
        "true",
        "yes",
        "1",
    )

    # Storage Service URL (validated at startup if USE_STORAGE_SERVICE=True)
    STORAGE_SERVICE_URL = os.environ.get("STORAGE_SERVICE_URL")
    STORAGE_REQUEST_TIMEOUT = int(os.environ.get("STORAGE_REQUEST_TIMEOUT", "30"))

    # Maximum avatar file size in MB
    MAX_AVATAR_SIZE_MB = int(os.environ.get("MAX_AVATAR_SIZE_MB", "5"))

    @classmethod
    def validate_storage_config(cls):
        """
        Validate Storage Service configuration coherence.

        Raises:
            ValueError: If USE_STORAGE_SERVICE is True but STORAGE_SERVICE_URL is not set.
        """
        if cls.USE_STORAGE_SERVICE:
            if not cls.STORAGE_SERVICE_URL:
                error_msg = (
                    "Configuration Error: USE_STORAGE_SERVICE is enabled (true) "
                    "but STORAGE_SERVICE_URL environment variable is not set. "
                    "Either set STORAGE_SERVICE_URL to a valid URL or disable "
                    "Storage Service integration by setting USE_STORAGE_SERVICE=false"
                )
                logger.error(error_msg)
                logger.error(
                    "Current environment variables: "
                    "USE_STORAGE_SERVICE=%s, STORAGE_SERVICE_URL=%s",
                    os.environ.get("USE_STORAGE_SERVICE", "not set"),
                    os.environ.get("STORAGE_SERVICE_URL", "not set"),
                )
                raise ValueError(error_msg)

            logger.info(
                "Storage Service integration enabled: %s",
                cls.STORAGE_SERVICE_URL,
            )
        else:
            logger.warning(
                "Storage Service integration is DISABLED. "
                "Avatar upload/download/delete operations will be skipped. "
                "This mode is intended for development/testing only."
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
        cls.validate_storage_config()


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
        cls.validate_storage_config()


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
        cls.validate_storage_config()


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
        cls.validate_storage_config()
