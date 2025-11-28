# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Test to demonstrate that JWT cookies are properly forwarded to Guardian service.
"""

import uuid
from unittest import mock

from tests.unit.conftest import create_jwt_token, get_init_db_payload


def test_jwt_cookie_forwarding_to_guardian(client, app):
    """
    Test that JWT cookies are properly forwarded to Guardian service calls.
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

    # Create JWT token
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service responses
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
            mock_response.json.return_value = {"roles": ["admin", "user"]}
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

    with mock.patch("requests.get", side_effect=mock_get_side_effect) as mock_get:
        with mock.patch("requests.post", return_value=mock_check_access):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response contains enriched roles
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert len(data["roles"]) == 2

            # Verify that the first call was to /user-roles with JWT
            first_call = mock_get.call_args_list[0]
            assert first_call[0][0] == "http://guardian:8000/user-roles"
            assert first_call[1]["params"] == {"user_id": user_id}
            assert first_call[1]["headers"] == {"Cookie": f"access_token={jwt_token}"}
            assert first_call[1]["timeout"] == 5

            # Extract the Cookie header that was sent to Guardian
            headers = first_call[1]["headers"]
            cookie_header = headers["Cookie"]

            # Verify the cookie contains our JWT token
            assert f"access_token={jwt_token}" in cookie_header
            print(
                f"✅ JWT token successfully forwarded to Guardian: {cookie_header[:50]}..."
            )


def test_post_role_jwt_cookie_forwarding(client, app):
    """
    Test that JWT cookies are forwarded in POST requests to Guardian service.
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

    # Create JWT token
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response
    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = str(uuid.uuid4())
    mock_response = mock.Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": user_id,
        "role_id": mock_role_id,
    }

    # Mock check_access response
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    def post_side_effect(url, **_kwargs):
        """Return different responses based on URL."""
        if "check-access" in url:
            return mock_check_access
        return mock_response

    with mock.patch(
        "requests.post", side_effect=post_side_effect
    ) as mock_post:
        payload = {"role_id": mock_role_id}
        response = client.post(f"/users/{user_id}/roles", json=payload)

        # Verify the response
        assert response.status_code == 201

        # Find the call to user-roles endpoint (not check-access)
        user_roles_calls = [
            call
            for call in mock_post.call_args_list
            if "user-roles" in call[0][0]
        ]
        assert len(user_roles_calls) == 1

        # Verify that the JWT cookie was forwarded to Guardian
        call_args = user_roles_calls[0]
        assert call_args[0][0] == "http://guardian:8000/user-roles"
        assert call_args[1]["json"] == {
            "user_id": user_id,
            "role_id": mock_role_id,
        }
        assert call_args[1]["headers"] == {
            "Cookie": f"access_token={jwt_token}"
        }
        assert call_args[1]["timeout"] == 5

        # Extract the Cookie header that was sent to Guardian
        headers = call_args[1]["headers"]
        cookie_header = headers["Cookie"]

        # Verify the cookie contains our JWT token
        assert f"access_token={jwt_token}" in cookie_header
        print(
            f"✅ JWT token successfully forwarded to Guardian in POST: {cookie_header[:50]}..."
        )


def test_individual_role_jwt_forwarding(client, app):
    """
    Test JWT forwarding for individual role operations (GET and DELETE).
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

    # Create JWT token
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = str(uuid.uuid4())

    # Test GET individual role
    mock_get_response = mock.Mock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": user_id,
        "role_id": mock_role_id,
    }

    # Mock check_access response
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    with mock.patch(
        "requests.get", return_value=mock_get_response
    ) as mock_get:
        with mock.patch("requests.post", return_value=mock_check_access):
            response = client.get(
                f"/users/{user_id}/roles/{mock_user_role_id}"
            )

            assert response.status_code == 200

            # Verify JWT forwarding for GET
            mock_get.assert_called_once_with(
                f"http://guardian:8000/user-roles/{mock_user_role_id}",
                headers={"Cookie": f"access_token={jwt_token}"},
                timeout=5,
            )
            print(
                "✅ JWT forwarded in individual role GET"
            )  # Test DELETE individual role
    mock_delete_response = mock.Mock()
    mock_delete_response.status_code = 204

    with mock.patch(
        "requests.get", return_value=mock_get_response
    ) as mock_get_del:
        with mock.patch(
            "requests.delete", return_value=mock_delete_response
        ) as mock_delete:
            with mock.patch("requests.post", return_value=mock_check_access):
                response = client.delete(
                    f"/users/{user_id}/roles/{mock_user_role_id}"
                )

                assert response.status_code == 204

                # Verify JWT forwarding for both GET (verification) and DELETE
                expected_headers = {"Cookie": f"access_token={jwt_token}"}

                mock_get_del.assert_called_once_with(
                    f"http://guardian:8000/user-roles/{mock_user_role_id}",
                    headers=expected_headers,
                    timeout=5,
                )

                mock_delete.assert_called_once_with(
                    f"http://guardian:8000/user-roles/{mock_user_role_id}",
                    headers=expected_headers,
                    timeout=5,
                )
                print(
                    "✅ JWT forwarded in individual role DELETE "
                    "(both GET verification and DELETE calls)"
                )
