# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Test to verify handling of different Guardian service response formats.
"""

from unittest import mock

from tests.unit.conftest import create_jwt_token, get_init_db_payload


def test_get_user_roles_with_direct_list_response(client, app):
    """
    Test GET /users/<user_id>/roles when Guardian returns a direct list.
    Tests that roles are enriched with full role details.
    """
    # Enable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = True
    app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response as direct list (user-role junction records)
    roles_data = [
        {"id": "ur1", "user_id": user_id, "role_id": "admin"},
        {"id": "ur2", "user_id": user_id, "role_id": "user"},
    ]
    
    # Mock enriched role details
    admin_role = {"id": "admin", "name": "Administrator", "description": "Admin role"}
    user_role = {"id": "user", "name": "User", "description": "User role"}

    # Mock check_access response
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    def mock_get_side_effect(url, *args, **kwargs):
        """Mock different responses based on URL"""
        if "/user-roles" in url:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = roles_data
            return mock_response
        elif "/roles/admin" in url:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = admin_role
            return mock_response
        elif "/roles/user" in url:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = user_role
            return mock_response
        return mock.Mock(status_code=404)

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch("requests.post", return_value=mock_check_access):
            response = client.get(f"/users/{user_id}/roles")

        # Verify the response contains enriched roles
        assert response.status_code == 200
        data = response.get_json()
        assert "roles" in data
        assert len(data["roles"]) == 2
        assert data["roles"][0] == admin_role
        assert data["roles"][1] == user_role
        print("✅ Direct list format handled correctly with role enrichment")


def test_get_user_roles_with_object_response(client, app):
    """
    Test GET /users/<user_id>/roles when Guardian returns an object with roles key.
    Tests that roles are enriched with full role details.
    """
    # Enable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = True
    app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response as object with roles key (user-role junction records)
    roles_data = [
        {"id": "ur1", "user_id": user_id, "role_id": "admin"},
        {"id": "ur2", "user_id": user_id, "role_id": "user"},
    ]
    
    # Mock enriched role details
    admin_role = {"id": "admin", "name": "Administrator", "description": "Admin role"}
    user_role = {"id": "user", "name": "User", "description": "User role"}

    # Mock check_access response
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    def mock_get_side_effect(url, *args, **kwargs):
        """Mock different responses based on URL"""
        if "/user-roles" in url:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"roles": roles_data}  # Object with roles key
            return mock_response
        elif "/roles/admin" in url:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = admin_role
            return mock_response
        elif "/roles/user" in url:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = user_role
            return mock_response
        return mock.Mock(status_code=404)

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch("requests.post", return_value=mock_check_access):
            response = client.get(f"/users/{user_id}/roles")

        # Verify the response contains enriched roles
        assert response.status_code == 200
        data = response.get_json()
        assert "roles" in data
        assert len(data["roles"]) == 2
        assert data["roles"][0] == admin_role
        assert data["roles"][1] == user_role
        print("✅ Object with roles key format handled correctly with role enrichment")


def test_get_user_roles_with_invalid_response_format(client, app):
    """
    Test GET /users/<user_id>/roles when Guardian returns an unexpected format.
    The API should gracefully handle this by returning an empty list with a 200 status.
    """
    # Enable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = True
    app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response with unexpected format
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "unexpected": "format"
    }  # Invalid format

    # Mock check_access response
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch("requests.post", return_value=mock_check_access):
            response = client.get(f"/users/{user_id}/roles")

        # Verify graceful handling: returns 200 with empty roles list
        # No enrichment happens because normalize_guardian_response returns empty list
        assert response.status_code == 200
        data = response.get_json()
        assert "roles" in data
        assert data["roles"] == []  # Should default to empty list
        print("✅ Invalid response format handled gracefully with empty roles")


def test_get_user_roles_empty_list(client, app):
    """
    Test GET /users/<user_id>/roles when user has no roles (empty list).
    """
    # Enable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = True
    app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response as empty list
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []  # Empty list

    # Mock check_access response
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch("requests.post", return_value=mock_check_access):
            response = client.get(f"/users/{user_id}/roles")

        # Verify the response
        assert response.status_code == 200
        data = response.get_json()
        assert "roles" in data
        assert data["roles"] == []
        print("✅ Empty roles list handled correctly")
