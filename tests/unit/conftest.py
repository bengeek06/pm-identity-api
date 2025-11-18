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


@pytest.fixture(autouse=True)
def clean_db(app):
    """
    Fixture automatique qui nettoie toutes les tables après chaque test.
    Garantit l'isolation complète entre les tests en supprimant les données
    dans l'ordre inverse des dépendances.
    Réinitialise également la configuration de l'application.
    """
    # Sauvegarde la configuration initiale
    original_config = {
        "USE_GUARDIAN_SERVICE": app.config.get("USE_GUARDIAN_SERVICE"),
        "USE_STORAGE_SERVICE": app.config.get("USE_STORAGE_SERVICE"),
    }
    
    yield
    
    # Après chaque test, on nettoie toutes les tables dans le bon ordre
    with app.app_context():
        # Import des modèles
        from app.models.user import User
        from app.models.position import Position
        from app.models.organization_unit import OrganizationUnit
        from app.models.customer import Customer
        from app.models.subcontractor import Subcontractor
        from app.models.company import Company
        
        # Supprime dans l'ordre : d'abord les entités qui dépendent d'autres
        try:
            db.session.query(User).delete()
            db.session.query(Position).delete()
            db.session.query(OrganizationUnit).delete()
            db.session.query(Customer).delete()
            db.session.query(Subcontractor).delete()
            db.session.query(Company).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
            # Si une erreur survient, on essaie avec PRAGMA
            db.session.execute(db.text("PRAGMA foreign_keys = OFF"))
            for table in reversed(db.metadata.sorted_tables):
                db.session.execute(table.delete())
            db.session.execute(db.text("PRAGMA foreign_keys = ON"))
            db.session.commit()
    
    # Restaure la configuration originale
    app.config.update(original_config)


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
