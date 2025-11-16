"""
Tests for database initialization via the /init-db endpoint.
"""

import pytest

from app.models.company import Company
from app.models.user import User


def get_valid_payload():
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


def test_get_returns_initialized_false(client):
    """
    Check that the GET /init-db endpoint returns initialized: False if no user exists.
    """
    resp = client.get("/init-db")
    assert resp.status_code == 200
    assert resp.json == {"initialized": False}


def test_post_success(client, session):
    """
    Check that a valid POST to /init-db initializes the database and returns the created entities.
    """
    payload = get_valid_payload()
    resp = client.post("/init-db", json=payload)
    assert resp.status_code == 201
    data = resp.json
    assert "company" in data
    assert "organization_unit" in data
    assert "position" in data
    assert "user" in data
    # Check DB state
    assert session.query(Company).count() == 1
    assert session.query(User).count() == 1


def test_post_already_initialized(client):
    """
    Check that a second POST to /init-db fails if the database is already initialized.
    """
    # First init
    payload = get_valid_payload()
    client.post("/init-db", json=payload)
    # Second init should fail
    resp = client.post("/init-db", json=payload)
    assert resp.status_code == 403
    assert (
        resp.json["message"].lower().startswith("identity already initialized")
    )


@pytest.mark.parametrize("missing_key", ["company", "user"])
def test_post_missing_data(client, missing_key):
    """
    Check that a POST to /init-db without one of the required keys returns a 400 error.
    """
    payload = get_valid_payload()
    del payload[missing_key]
    resp = client.post("/init-db", json=payload)
    assert resp.status_code == 400
    assert "required" in resp.json["message"]
