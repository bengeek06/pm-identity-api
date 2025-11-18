"""
Test to verify Guardian Service can be disabled via USE_GUARDIAN_SERVICE config.
"""

from tests.conftest import create_jwt_token, get_init_db_payload


def test_guardian_service_disabled_returns_empty_roles(client, app):
    """
    Test that when USE_GUARDIAN_SERVICE=false, user roles endpoint returns empty list.
    """
    # Disable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = False

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Request user roles - should return empty list without calling Guardian
    response = client.get(f"/users/{user_id}/roles")
    assert response.status_code == 200
    data = response.get_json()
    assert "roles" in data
    assert data["roles"] == []


def test_guardian_service_disabled_returns_empty_permissions(client, app):
    """
    Test that when USE_GUARDIAN_SERVICE=false, user permissions endpoint returns empty list.
    """
    # Disable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = False

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Request user permissions - should return empty list without calling Guardian
    response = client.get(f"/users/{user_id}/permissions")
    assert response.status_code == 200
    data = response.get_json()
    assert "permissions" in data
    assert data["permissions"] == []


def test_guardian_service_disabled_returns_empty_policies(client, app):
    """
    Test that when USE_GUARDIAN_SERVICE=false, user policies endpoint returns empty list.
    """
    # Disable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = False

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Request user policies - should return empty list without calling Guardian
    response = client.get(f"/users/{user_id}/policies")
    assert response.status_code == 200
    data = response.get_json()
    assert "policies" in data
    assert data["policies"] == []


def test_guardian_service_disabled_post_role_returns_503(client, app):
    """
    Test that when USE_GUARDIAN_SERVICE=false, POST user role returns 503.
    """
    # Disable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = False

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to assign a role - should return 503 Service Unavailable
    response = client.post(
        f"/users/{user_id}/roles",
        json={"role_id": "admin"},
    )
    assert response.status_code == 503
    data = response.get_json()
    assert "Guardian Service is disabled" in data["message"]


def test_guardian_service_disabled_get_individual_role_returns_503(
    client, app
):
    """
    Test that when USE_GUARDIAN_SERVICE=false, GET individual role returns 503.
    """
    # Disable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = False

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to get a specific role - should return 503 Service Unavailable
    fake_role_id = "role123"
    response = client.get(f"/users/{user_id}/roles/{fake_role_id}")
    assert response.status_code == 503
    data = response.get_json()
    assert "Guardian Service is disabled" in data["message"]


def test_guardian_service_disabled_delete_role_returns_503(client, app):
    """
    Test that when USE_GUARDIAN_SERVICE=false, DELETE role returns 503.
    """
    # Disable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = False

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to delete a role - should return 503 Service Unavailable
    fake_role_id = "role123"
    response = client.delete(f"/users/{user_id}/roles/{fake_role_id}")
    assert response.status_code == 503
    data = response.get_json()
    assert "Guardian Service is disabled" in data["message"]


def test_guardian_service_disabled_bypasses_access_control(client, app):
    """
    Test that when USE_GUARDIAN_SERVICE=false, access control checks are bypassed.
    This allows endpoints to work without Guardian being available.
    """
    # Disable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = False

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Access should work without Guardian for regular endpoints
    # For example, GET user should work
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    # This demonstrates that access control is bypassed when Guardian is disabled
