"""
conftest.py - Integration Test Fixtures

Fixtures for integration tests with real Storage Service.
All interactions go through Storage Service API, never directly to MinIO.
"""

import os
import uuid

import pytest
import requests
from werkzeug.security import generate_password_hash

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
    except (requests.exceptions.RequestException, AssertionError) as e:
        pytest.skip(
            f"Storage Service not available at {storage_url}: {e}\n"
            "Run: docker-compose -f docker-compose.integration.yml up -d"
        )


@pytest.fixture
def integration_app(
    integration_config, check_services_health
):  # pylint: disable=unused-argument
    """
    Flask app configured for integration testing with real Storage Service.

    Args:
        integration_config: Configuration dictionary for integration tests
        check_services_health: Fixture that verifies services are healthy (implicit dependency)
    """
    # Save original environment variables to restore after tests
    original_env = {
        "USE_STORAGE_SERVICE": os.environ.get("USE_STORAGE_SERVICE"),
        "STORAGE_SERVICE_URL": os.environ.get("STORAGE_SERVICE_URL"),
        "JWT_SECRET": os.environ.get("JWT_SECRET"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "FLASK_ENV": os.environ.get("FLASK_ENV"),
    }

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

    # Restore original environment variables
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


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
        """Helper class for making authenticated requests to Storage Service API."""

        def __init__(self, base_url):
            self.base_url = base_url

        def get_file_metadata(
            self,
            file_id,
            company_id,
            user_id,
            bucket="users",
            resource_type="avatars",
        ):
            """
            Get file metadata from Storage Service using /metadata endpoint.

            Args:
                file_id: File ID (for reference, not used in API call)
                company_id: Company ID - used as bucket_id for company logos
                user_id: User ID - used as bucket_id for user avatars
                bucket: Bucket type ("users" for avatars, "companies" for logos)
                resource_type: Resource type ("avatars" or "logos")

            Returns:
                Response object with status_code and json() method
            """
            # Determine bucket_id based on bucket type
            bucket_id = company_id if bucket == "companies" else user_id

            # Determine logical path based on resource type
            logical_path = f"{resource_type}/{bucket_id}.png"

            response = requests.get(
                f"{self.base_url}/metadata",
                params={
                    "bucket": bucket,
                    "id": bucket_id,
                    "logical_path": logical_path,
                    "include_versions": False,
                },
                headers={
                    "X-Company-ID": company_id,
                    "X-User-ID": user_id,
                },
                timeout=5,
            )
            return response

        def delete_file(self, file_id, company_id, user_id):
            """Delete file via Storage Service /delete endpoint."""
            response = requests.delete(
                f"{self.base_url}/delete",
                json={"file_id": file_id, "physical": True},
                headers={
                    "X-Company-ID": company_id,
                    "X-User-ID": user_id,
                },
                timeout=5,
            )
            return response

    return StorageAPIClient(integration_config["STORAGE_SERVICE_URL"])
