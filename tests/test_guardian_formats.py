"""
Test to verify handling of different Guardian service response formats.
"""

from unittest import mock

from tests.conftest import get_init_db_payload, create_jwt_token


def test_get_user_roles_with_direct_list_response(client):
    """
    Test GET /users/<user_id>/roles when Guardian returns a direct list.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response as direct list
    junction_data = [
        {"id": "role1", "user_id": user_id, "role_id": "admin"},
        {"id": "role2", "user_id": user_id, "role_id": "user"},
    ]

    # Mock enriched role objects
    admin_role = {
        "id": "admin",
        "name": "Admin",
        "description": "Administrator role",
    }
    user_role = {
        "id": "user",
        "name": "User",
        "description": "Regular user role",
    }

    def mock_get_side_effect(url, **kwargs):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        if "/user-roles" in url:
            mock_resp.json.return_value = junction_data  # Direct list
        elif "/roles/admin" in url:
            mock_resp.json.return_value = admin_role
        elif "/roles/user" in url:
            mock_resp.json.return_value = user_role
        return mock_resp

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            # Now we expect enriched role objects, not junction records
            assert len(data["roles"]) == 2
            assert data["roles"][0] == admin_role
            assert data["roles"][1] == user_role
            print("✅ Direct list format handled correctly")


def test_get_user_roles_with_object_response(client):
    """
    Test GET /users/<user_id>/roles when Guardian returns an object with roles key.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response as object with roles key
    junction_data = [
        {"id": "role1", "user_id": user_id, "role_id": "admin"},
        {"id": "role2", "user_id": user_id, "role_id": "user"},
    ]

    # Mock enriched role objects
    admin_role = {
        "id": "admin",
        "name": "Admin",
        "description": "Administrator role",
    }
    user_role = {
        "id": "user",
        "name": "User",
        "description": "Regular user role",
    }

    def mock_get_side_effect(url, **kwargs):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        if "/user-roles" in url:
            mock_resp.json.return_value = {
                "roles": junction_data
            }  # Object with roles key
        elif "/roles/admin" in url:
            mock_resp.json.return_value = admin_role
        elif "/roles/user" in url:
            mock_resp.json.return_value = user_role
        return mock_resp

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            # Now we expect enriched role objects, not junction records
            assert len(data["roles"]) == 2
            assert data["roles"][0] == admin_role
            assert data["roles"][1] == user_role
            print("✅ Object with roles key format handled correctly")


def test_get_user_roles_with_invalid_response_format(client):
    """
    Test GET /users/<user_id>/roles when Guardian returns an unexpected format.
    The API should gracefully handle this by returning an empty list with a 200 status.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response with unexpected format
    def mock_get_side_effect(url, **kwargs):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        if "/user-roles" in url:
            mock_resp.json.return_value = {
                "unexpected": "format"
            }  # Invalid format
        return mock_resp

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            response = client.get(f"/users/{user_id}/roles")

            # Verify graceful handling: returns 200 with empty roles list
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == []  # Should default to empty list
            print(
                "✅ Invalid response format handled gracefully with empty roles"
            )


def test_get_user_roles_empty_list(client):
    """
    Test GET /users/<user_id>/roles when user has no roles (empty list).
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response as empty list
    def mock_get_side_effect(url, **kwargs):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        if "/user-roles" in url:
            mock_resp.json.return_value = []  # Empty list
        return mock_resp

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == []
            print("✅ Empty roles list handled correctly")
