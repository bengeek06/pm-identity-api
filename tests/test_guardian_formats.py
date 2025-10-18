"""
Test to verify handling of different Guardian service response formats.
"""

import uuid
from unittest import mock
from tests.conftest import get_init_db_payload, create_jwt_token


def test_get_user_roles_with_direct_list_response(client, session):
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
    roles_data = [
        {"id": "role1", "user_id": user_id, "role_id": "admin"},
        {"id": "role2", "user_id": user_id, "role_id": "user"}
    ]
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = roles_data  # Direct list

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict("os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == roles_data
            print("✅ Direct list format handled correctly")


def test_get_user_roles_with_object_response(client, session):
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
    roles_data = [
        {"id": "role1", "user_id": user_id, "role_id": "admin"},
        {"id": "role2", "user_id": user_id, "role_id": "user"}
    ]
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"roles": roles_data}  # Object with roles key

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict("os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == roles_data
            print("✅ Object with roles key format handled correctly")


def test_get_user_roles_with_invalid_response_format(client, session):
    """
    Test GET /users/<user_id>/roles when Guardian returns an unexpected format.
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
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"unexpected": "format"}  # Invalid format

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict("os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}):
            response = client.get(f"/users/{user_id}/roles")

            # Verify error handling
            assert response.status_code == 500
            data = response.get_json()
            assert "message" in data
            assert "Error fetching roles" in data["message"]
            print("✅ Invalid response format handled correctly")


def test_get_user_roles_empty_list(client, session):
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
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []  # Empty list

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict("os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == []
            print("✅ Empty roles list handled correctly")