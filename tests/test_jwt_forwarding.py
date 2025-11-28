"""
Test to demonstrate that JWT cookies are properly forwarded to Guardian service.
"""

from unittest import mock
import uuid

from tests.test_user import get_init_db_payload, create_jwt_token


def test_jwt_cookie_forwarding_to_guardian(client):
    """
    Test that JWT cookies are properly forwarded to Guardian service calls.
    """
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
    junction_data = [
        {"id": "ur1", "user_id": user_id, "role_id": "admin"},
        {"id": "ur2", "user_id": user_id, "role_id": "user"},
    ]
    admin_role = {"id": "admin", "name": "Admin"}
    user_role = {"id": "user", "name": "User"}

    def mock_get_side_effect(url, **kwargs):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        if "/user-roles" in url:
            mock_resp.json.return_value = {"roles": junction_data}
        elif "/roles/admin" in url:
            mock_resp.json.return_value = admin_role
        elif "/roles/user" in url:
            mock_resp.json.return_value = user_role
        return mock_resp

    with mock.patch(
        "requests.get", side_effect=mock_get_side_effect
    ) as mock_get:
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200

            # Verify that the JWT cookie was forwarded to Guardian
            # Should have 3 calls: /user-roles, /roles/admin, /roles/user
            assert mock_get.call_count == 3

            # Check first call (junction records)
            first_call = mock_get.call_args_list[0]
            assert "http://guardian:5000/user-roles" in first_call[0][0]
            assert (
                first_call[1]["headers"]["Cookie"]
                == f"access_token={jwt_token}"
            )

            # Verify all calls have JWT cookie
            for call in mock_get.call_args_list:
                headers = call[1]["headers"]
                cookie_header = headers["Cookie"]
                assert f"access_token={jwt_token}" in cookie_header

            print(
                f"✅ JWT token successfully forwarded to Guardian in all {mock_get.call_count} calls"
            )


def test_post_role_jwt_cookie_forwarding(client):
    """
    Test that JWT cookies are forwarded in POST requests to Guardian service.
    """
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

    with mock.patch("requests.post", return_value=mock_response) as mock_post:
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            payload = {"role_id": mock_role_id}
            response = client.post(f"/users/{user_id}/roles", json=payload)

            # Verify the response
            assert response.status_code == 201

            # Verify that the JWT cookie was forwarded to Guardian
            mock_post.assert_called_once_with(
                "http://guardian:5000/user-roles",
                json={"user_id": user_id, "role_id": mock_role_id},
                headers={"Cookie": f"access_token={jwt_token}"},
                timeout=5,
            )

            # Extract the Cookie header that was sent to Guardian
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            cookie_header = headers["Cookie"]

            # Verify the cookie contains our JWT token
            assert f"access_token={jwt_token}" in cookie_header
            print(
                f"✅ JWT token successfully forwarded to Guardian in POST: {cookie_header[:50]}..."
            )


def test_individual_role_jwt_forwarding(client):
    """
    Test JWT forwarding for individual role operations (GET and DELETE).
    """
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

    with mock.patch(
        "requests.get", return_value=mock_get_response
    ) as mock_get:
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            response = client.get(
                f"/users/{user_id}/roles/{mock_user_role_id}"
            )

            assert response.status_code == 200

            # Verify JWT forwarding for GET
            mock_get.assert_called_once_with(
                f"http://guardian:5000/user-roles/{mock_user_role_id}",
                headers={"Cookie": f"access_token={jwt_token}"},
                timeout=5,
            )
            print("✅ JWT forwarded in individual role GET")

    # Test DELETE individual role
    mock_delete_response = mock.Mock()
    mock_delete_response.status_code = 204

    with mock.patch(
        "requests.get", return_value=mock_get_response
    ) as mock_get_del:
        with mock.patch(
            "requests.delete", return_value=mock_delete_response
        ) as mock_delete:
            with mock.patch.dict(
                "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
            ):
                response = client.delete(
                    f"/users/{user_id}/roles/{mock_user_role_id}"
                )

                assert response.status_code == 204

                # Verify JWT forwarding for both GET (verification) and DELETE
                expected_headers = {"Cookie": f"access_token={jwt_token}"}

                mock_get_del.assert_called_once_with(
                    f"http://guardian:5000/user-roles/{mock_user_role_id}",
                    headers=expected_headers,
                    timeout=5,
                )

                mock_delete.assert_called_once_with(
                    f"http://guardian:5000/user-roles/{mock_user_role_id}",
                    headers=expected_headers,
                    timeout=5,
                )
                print(
                    "✅ JWT forwarded in individual role DELETE "
                    "(both GET verification and DELETE calls)"
                )
