"""
# conftest.py
# -----------
"""

import os

import jwt
from dotenv import load_dotenv
from pytest import fixture

# Load .env.test FIRST, before any imports from app
# This ensures config.py reads the correct environment variables
# Chargement de l'environnement de test
os.environ["FLASK_ENV"] = "testing"
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.test")
)

# Set additional environment variables for testing
# These override .env.test if needed
# os.environ["FLASK_ENV"] = "testing"
# os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import create_app
from app.models import db


@fixture(autouse=True, scope="function")
def reset_test_environment():
    """
    Automatically reset test environment variables before each test.
    This ensures integration tests don't pollute unit tests with their config.
    """
    # Save current values
    original_use_storage = os.environ.get("USE_STORAGE_SERVICE")

    # Force test environment values for unit tests
    # (integration tests will override these in their own fixtures)
    os.environ["USE_STORAGE_SERVICE"] = "false"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    yield

    # Restore original if it existed, otherwise remove
    if original_use_storage is not None:
        os.environ["USE_STORAGE_SERVICE"] = original_use_storage


@fixture
def app():
    """
    Fixture to create and configure a Flask application for testing.
    This fixture sets up the application context, initializes the database,
    and ensures that the database is created before tests run and dropped after tests complete.
    """
    # Force reload of config by reimporting it
    import importlib

    from app import config

    importlib.reload(config)

    app = create_app("app.config.TestingConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@fixture
def client(app):
    """
    Fixture to create a test client for the Flask application.
    This client can be used to simulate HTTP requests to the application.
    """
    return app.test_client()


@fixture
def session(app):
    """
    Fixture to provide a database session for tests.
    This session is scoped to the application context and can be used
    to interact with the database during tests.
    """
    with app.app_context():
        yield db.session


def get_init_db_payload():
    """
    Generate a valid payload for full database initialization via /init-db.
    Returns a dictionary containing data for company, organization_unit, position, and user.
    """
    return {
        "company": {"name": "TestCorp", "description": "A test company"},
        "organization_unit": {
            "name": "Direction",
            "description": "Direction générale",
        },
        "position": {"title": "CEO", "description": "Chief Executive Officer"},
        "user": {
            "email": "admin@testcorp.com",
            "first_name": "Alice",
            "last_name": "Admin",
            "password": "supersecret",
        },
    }


def create_jwt_token(company_id, user_id):
    """Helper function to create a JWT token for testing."""
    jwt_secret = os.environ.get("JWT_SECRET", "test_secret")
    payload = {"company_id": company_id, "user_id": user_id}
    return jwt.encode(payload, jwt_secret, algorithm="HS256")
