"""
conftest.py - Integration Test Fixtures

Fixtures for integration tests with real Storage Service.
All interactions go through Storage Service API, never directly to MinIO.
"""

import os
import uuid

import pytest
import requests

from app import create_app
from app.models import db
from app.models.company import Company
from app.models.user import User
from tests.conftest import create_jwt_token


@pytest.fixture(scope="session")
def integration_config():
    """
    Configuration for integration tests.
    Override environment variables to point to real Storage Service.
    """
    config = {
        "STORAGE_SERVICE_URL": os.getenv(
            "STORAGE_SERVICE_URL", "http://localhost:5001"
        ),
        "JWT_SECRET": "integration-test-secret-key",
    }
    return config


@pytest.fixture(scope="session")
def check_services_health(integration_config):
    """
    Verify that Storage Service is healthy before running tests.
    We only check Storage Service, not MinIO directly.
    """
    storage_url = integration_config["STORAGE_SERVICE_URL"]

    # Check Storage Service
    try:
        response = requests.get(f"{storage_url}/health", timeout=5)
        assert (
            response.status_code == 200
        ), f"Storage Service unhealthy: {response.status_code}"
        print(f"✓ Storage Service healthy at {storage_url}")
    except Exception as e:
        pytest.skip(
            f"Storage Service not available at {storage_url}: {e}\n"
            "Run: docker-compose -f docker-compose.integration.yml up -d"
        )


@pytest.fixture
def integration_app(integration_config, check_services_health):
    """
    Flask app configured for integration testing with real Storage Service.
    """
    # Set environment variables for real services
    os.environ["USE_STORAGE_SERVICE"] = "true"
    os.environ["STORAGE_SERVICE_URL"] = integration_config[
        "STORAGE_SERVICE_URL"
    ]
    os.environ["JWT_SECRET"] = integration_config["JWT_SECRET"]
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["FLASK_ENV"] = "testing"

    app = create_app("app.config.TestingConfig")

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def integration_client(integration_app):
    """
    Test client for integration tests.
    """
    return integration_app.test_client()


@pytest.fixture
def integration_session(integration_app):
    """
    Database session for integration tests.
    """
    with integration_app.app_context():
        yield db.session


@pytest.fixture
def real_company(integration_session):
    """
    Create a real company for integration tests.
    """
    company = Company(id=str(uuid.uuid4()), name="Integration Test Corp")
    integration_session.add(company)
    integration_session.commit()
    yield company
    integration_session.delete(company)
    integration_session.commit()


@pytest.fixture
def real_user(integration_session, real_company):
    """
    Create a real user for integration tests.
    """
    from werkzeug.security import generate_password_hash
    
    user = User(
        id=str(uuid.uuid4()),
        email="integration@test.com",
        first_name="Integration",
        last_name="Test",
        company_id=real_company.id,
        hashed_password=generate_password_hash("integration-password"),
    )
    integration_session.add(user)
    integration_session.commit()
    yield user
    integration_session.delete(user)
    integration_session.commit()


@pytest.fixture
def integration_token(real_company, real_user):
    """
    Generate JWT token for integration tests.
    """
    return create_jwt_token(real_company.id, real_user.id)


@pytest.fixture
def storage_api_client(integration_config):
    """
    HTTP client for direct Storage Service API calls.
    """

    class StorageAPIClient:
        def __init__(self, base_url):
            self.base_url = base_url

        def get_file_metadata(self, file_id, company_id, user_id):
            """Get file metadata from Storage Service."""
            response = requests.get(
                f"{self.base_url}/files/{file_id}",
                headers={
                    "X-Company-ID": company_id,
                    "X-User-ID": user_id,
                },
                timeout=5,
            )
            return response

        def delete_file(self, file_id, company_id, user_id):
            """Delete file via Storage Service."""
            response = requests.delete(
                f"{self.base_url}/files/{file_id}",
                headers={
                    "X-Company-ID": company_id,
                    "X-User-ID": user_id,
                },
                timeout=5,
            )
            return response

    return StorageAPIClient(integration_config["STORAGE_SERVICE_URL"])
