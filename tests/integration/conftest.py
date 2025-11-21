# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
conftest.py - Integration Test Fixtures

Fixtures for integration tests with real Storage Service.
All interactions go through Storage Service API, never directly to MinIO.
"""

import os

import jwt
import pytest
import requests

from app import create_app
from app.models import db
from app.models.company import Company
from app.models.user import User


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
    Verify that Storage Service and Guardian Service are healthy before running tests.
    """
    storage_url = integration_config["STORAGE_SERVICE_URL"]
    guardian_url = "http://localhost:5002"  # Guardian Service URL

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
            "Run: docker-compose -f docker-compose.test.yml --profile guardian up -d"
        )

    # Check Guardian Service
    try:
        response = requests.get(f"{guardian_url}/health", timeout=5)
        assert (
            response.status_code == 200
        ), f"Guardian Service unhealthy: {response.status_code}"
        print(f"✓ Guardian Service healthy at {guardian_url}")
    except (requests.exceptions.RequestException, AssertionError) as e:
        pytest.skip(
            f"Guardian Service not available at {guardian_url}: {e}\n"
            "Run: ./scripts/run-integration-tests.sh"
        )


@pytest.fixture(scope="session")
def integration_app(
    integration_config, check_services_health
):  # pylint: disable=unused-argument
    """
    Flask app configured for integration testing with real Storage Service.
    Session-scoped to share the same app across all tests.

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


@pytest.fixture(scope="session")
def integration_client(integration_app):
    """
    Test client for integration tests.
    Session-scoped to share the same client across all tests.
    """
    return integration_app.test_client()


@pytest.fixture(scope="session")
def integration_session():
    """
    Database session for integration tests.
    Session-scoped - yields the session for the entire test session.
    """
    # Don't use with app_context here - it's already active in integration_app
    return db.session


@pytest.fixture(scope="session")
def integration_identity_init(integration_client):
    """
    Initialize Identity Service via /init-db endpoint.
    Returns the created company and user data including IDs.
    Session-scoped to run once for all tests.
    """
    # Call Identity /init-db to create company and user
    response = integration_client.post(
        "/init-db",
        json={
            "company": {"name": "Integration Test Corp"},
            "user": {
                "email": "admin@integration-test.com",
                "password": "integration-password",
                "first_name": "Admin",
                "last_name": "User",
            },
        },
    )

    assert (
        response.status_code == 201
    ), f"Identity init failed: {response.get_json()}"
    data = response.get_json()

    company_id = data["company"]["id"]
    user_id = data["user"]["id"]

    return {
        "company_id": company_id,
        "user_id": user_id,
        "company": data["company"],
        "user": data["user"],
    }


@pytest.fixture(scope="session")
def guardian_init(integration_identity_init):
    """
    Initialize Guardian Service via /init-db endpoint.
    Uses company_id and user_id from Identity initialization.
    Session-scoped to run once for all tests.

    Returns the role name (companyadmin) created by Guardian.
    """
    guardian_url = "http://localhost:5002"

    company_id = integration_identity_init["company_id"]
    user_id = integration_identity_init["user_id"]

    print(
        f"✓ Initializing Guardian - company_id={company_id}, user_id={user_id}"
    )

    # Call Guardian /init-db to create policies, roles, and assign role to user
    try:
        response = requests.post(
            f"{guardian_url}/init-db",
            json={"company": {"id": company_id}, "user": {"id": user_id}},
            timeout=10,
        )

        # Accept both 201 (created) and 403 (already initialized)
        if response.status_code == 201:
            print("✓ Guardian initialized successfully")
        elif response.status_code == 403:
            print("✓ Guardian already initialized")
        else:
            print(
                f"❌ Guardian init failed: {response.status_code} - {response.text}"
            )
            response.raise_for_status()

        return "companyadmin"

    except requests.exceptions.RequestException as e:
        pytest.skip(f"Guardian Service not available: {e}")
        return None


@pytest.fixture
def integration_token(integration_identity_init, guardian_init):  # pylint: disable=unused-argument
    """
    Generate JWT token for integration tests.
    Uses the company_id and user_id from Identity initialization.

    Depends on guardian_init to ensure Guardian is initialized before tests run.
    """
    company_id = integration_identity_init["company_id"]
    user_id = integration_identity_init["user_id"]

    return create_jwt_token(company_id, user_id)


@pytest.fixture
def storage_api_client(integration_config):
    """
    HTTP client for direct Storage Service API calls.
    Uses JWT authentication via cookie (same as Identity Service).
    """

    class StorageAPIClient:
        """Helper class for making authenticated requests to Storage Service API."""

        def __init__(self, base_url, jwt_secret):
            self.base_url = base_url
            self.jwt_secret = jwt_secret
            self.session = requests.Session()

        def _set_jwt_cookie(self, company_id, user_id):
            """Set JWT cookie for authentication."""
            token = create_jwt_token(company_id, user_id)
            # Storage Service uses 'access_token' cookie for JWT
            self.session.cookies.set("access_token", token, domain="localhost")

        def get_file_metadata(
            self,
            _file_id,
            company_id,
            user_id,
            bucket="users",
            resource_type="avatars",
        ):
            """
            Get file metadata from Storage Service using /metadata endpoint.

            API specification from openapi.yml:
            - bucket: Bucket type enum [users, companies, projects]
            - id: Bucket ID (user_id, company_id, or project_id)
            - logical_path: File path within bucket
            - include_versions: boolean (optional, default false)

            Args:
                file_id: File ID (not used in query, just for reference)
                company_id: Company ID
                user_id: User ID
                bucket: Bucket type ("users" for avatars, "companies" for logos)
                resource_type: Resource type ("avatars" or "logos")

            Returns:
                Response object with status_code and json() method
            """
            # Set JWT cookie for authentication
            self._set_jwt_cookie(company_id, user_id)

            # For avatars: bucket="users", id=user_id
            # For logos: bucket="companies", id=company_id
            bucket_id = company_id if bucket == "companies" else user_id

            # Logical path is resource_type/bucket_id.extension
            logical_path = f"{resource_type}/{bucket_id}.png"

            # API uses: bucket (type), id (bucket_id), logical_path
            response = self.session.get(
                f"{self.base_url}/metadata",
                params={
                    "bucket": bucket,  # "users" or "companies"
                    "id": bucket_id,  # user_id or company_id
                    "logical_path": logical_path,
                    "include_versions": False,
                },
                timeout=5,
            )
            return response

        def delete_file(self, file_id, company_id, user_id):
            """
            Delete file via Storage Service /delete endpoint.

            Uses JWT cookie authentication instead of headers.
            """
            # Set JWT cookie for authentication
            self._set_jwt_cookie(company_id, user_id)

            response = self.session.delete(
                f"{self.base_url}/delete",
                json={"file_id": file_id, "physical": True},
                timeout=5,
            )
            return response

    return StorageAPIClient(
        integration_config["STORAGE_SERVICE_URL"],
        integration_config["JWT_SECRET"],
    )


def create_jwt_token(company_id, user_id):
    """Helper function to create a JWT token for testing."""
    jwt_secret = os.environ.get("JWT_SECRET", "test_secret")
    payload = {"company_id": company_id, "user_id": user_id}
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


# ============================================================================
# Backward compatibility aliases for existing tests
# ============================================================================


@pytest.fixture
def real_company(integration_identity_init, integration_app):
    """
    Backward compatibility alias for tests expecting real_company.
    Returns a Company object with data from Identity /init-db.
    """
    with integration_app.app_context():
        company_data = integration_identity_init["company"]
        # Return a Company object that looks like it came from the DB
        company = Company(id=company_data["id"], name=company_data["name"])
        return company


@pytest.fixture
def real_user(
    integration_identity_init,
    integration_app,
    guardian_init,  # pylint: disable=unused-argument
    integration_token,  # pylint: disable=unused-argument
):
    """
    Backward compatibility alias for tests expecting real_user.
    Returns a User object with data from Identity /init-db.
    Guardian role is already assigned via guardian_init.
    """
    with integration_app.app_context():
        user_data = integration_identity_init["user"]
        # Return a User object that looks like it came from the DB
        user = User(
            id=user_data["id"],
            email=user_data["email"],
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            company_id=integration_identity_init["company_id"],
        )
        return user
