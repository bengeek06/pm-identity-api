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

import os


class Config:
    """
    Base configuration common to all environments.

    Attributes:
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Disable SQLAlchemy event system.
        MAX_CONTENT_LENGTH (int): Maximum allowed request size in bytes (16 MB).
    """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Allow uploads up to 16 MB (enough for avatar images)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB


class DevelopmentConfig(Config):
    """
    Configuration for the development environment.

    Attributes:
        DEBUG (bool): Enable debug mode.
        SQLALCHEMY_DATABASE_URI (str): Database URI for development.
    """

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
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
    if not SQLALCHEMY_DATABASE_URI:
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
    if not SQLALCHEMY_DATABASE_URI:
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
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable is not set.")
