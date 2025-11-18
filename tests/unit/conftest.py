"""
# conftest.py
# -----------
"""

import os

import jwt
import pytest

from app import create_app
from app.models import db


@pytest.fixture(scope="session")
def app():
    """
    Crée et configure l'application Flask pour les tests.
    Initialise la base, crée et drop toutes les tables pour chaque session de test.
    """
    app = create_app("app.config.TestingConfig")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """
    Fournit un client Flask pour les requêtes HTTP de test.
    """
    return app.test_client()


@pytest.fixture
def session(app):
    """
    Fournit une session SQLAlchemy liée à l'app Flask de test.
    """
    with app.app_context():
        yield db.session
        db.session.remove()


def create_jwt_token(company_id, user_id):
    """Helper function to create a JWT token for testing."""
    jwt_secret = os.environ.get("JWT_SECRET", "test_secret")
    payload = {"company_id": company_id, "user_id": user_id}
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


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
