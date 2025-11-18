"""
Test cases for the UserResource class in the PM Identity API.
"""

# pylint: disable=too-many-locals,too-many-statements,unused-argument

import os
import uuid
from unittest import mock

import jwt
import pytest
import requests
from werkzeug.security import generate_password_hash

from app.models.user import User
from tests.unit.conftest import create_jwt_token, get_init_db_payload


##################################################
# Test cases for GET /users
##################################################
def test_get_users_empty(client, session):
    """
    Test GET /users when there are no other users in the company.
    """
    # Create a company and user for authentication, but no other users
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Remove the user that was created by init-db to test empty state
    user = User.get_by_id(user_id)
    session.delete(user)
    session.commit()

    response = client.get("/users")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_users_single(client, session):
    """
    Test GET /users with a single user.
    """
    company_id = str(uuid.uuid4())
    user = User(
        email="test1@example.com",
        hashed_password="hashedpw1",
        first_name="Alice",
        last_name="Smith",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    # Create JWT token for authentication
    jwt_token = create_jwt_token(company_id, str(user.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get("/users")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["email"] == "test1@example.com"
    assert data[0]["first_name"] == "Alice"
    assert data[0]["last_name"] == "Smith"
    assert data[0]["company_id"] == company_id
    assert "id" in data[0]


def test_get_users_multiple(client, session):
    """
    Test GET /users with multiple users.
    """
    company_id = str(uuid.uuid4())
    user1 = User(
        email="test2@example.com",
        hashed_password="hashedpw2",
        first_name="Bob",
        last_name="Jones",
        company_id=company_id,
    )
    user2 = User(
        email="test3@example.com",
        hashed_password="hashedpw3",
        first_name="Carol",
        last_name="Brown",
        company_id=company_id,
    )
    session.add_all([user1, user2])
    session.commit()

    # Create JWT token for authentication using the first user
    jwt_token = create_jwt_token(company_id, str(user1.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get("/users")
    assert response.status_code == 200
    data = response.get_json()
    emails = [item["email"] for item in data]
    assert "test2@example.com" in emails
    assert "test3@example.com" in emails
    first_names = [item["first_name"] for item in data]
    assert "Bob" in first_names
    assert "Carol" in first_names


##################################################
# Test cases for POST /users
##################################################


def test_post_user_success(client):
    """
    Test POST /users with valid data.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {
        "email": "newuser@example.com",
        "password": "MySecret123!",
        "first_name": "John",
        "last_name": "Doe",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["email"] == "newuser@example.com"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["company_id"] == str(company_id)
    assert "id" in data


def test_post_user_missing_required_fields(client):
    """
    Test POST /users with missing required fields.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {
        "email": "nouser@example.com"
        # missing password, first_name, last_name, company_id
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    # At least one required field should be mentioned in the error
    assert (
        "password" in str(data).lower()
        or "first_name" in str(data).lower()
        or "last_name" in str(data).lower()
        or "company_id" in str(data).lower()
    )


def test_post_user_duplicate_email(client, session):
    """
    Test POST /users with duplicate email.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    user = User(
        email="dup@example.com",
        hashed_password="hashedpw",
        first_name="Dup",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()
    payload = {
        "email": "dup@example.com",
        "password": "AnotherSecret!",
        "first_name": "Dup",
        "last_name": "User",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in str(data).lower()


def test_post_user_invalid_email(client):
    """
    Test POST /users with invalid email format.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {
        "email": "not-an-email",
        "password": "Secret123!",
        "first_name": "Bad",
        "last_name": "Email",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in str(data).lower()


##################################################
# Test cases for GET /users/<id>
##################################################


def test_get_user_by_id_success(client, session):
    """
    Test GET /users/<id> for an existing user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    user = User(
        email="uniqueuser@example.com",
        hashed_password="hashedpw",
        first_name="Unique",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    response = client.get(f"/users/{user.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == str(user.id)
    assert data["email"] == "uniqueuser@example.com"
    assert data["first_name"] == "Unique"
    assert data["last_name"] == "User"
    assert data["company_id"] == company_id


def test_get_user_by_id_not_found(client):
    """
    Test GET /users/<id> for a non-existent user.
    """
    fake_id = str(uuid.uuid4())
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get(f"/users/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert (
        "not found" in str(data).lower()
        or "error" in data
        or "message" in data
    )


##################################################
# Test cases for PUT /users/<id>
##################################################


def test_put_user_success(client, session):
    """
    Test PUT /users/<id> for a full update.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    user = User(
        email="old@example.com",
        hashed_password="oldhash",
        first_name="Old",
        last_name="Name",
        company_id=str(company_id),
    )
    session.add(user)
    session.commit()

    payload = {
        "email": "updated@example.com",
        "password": "NewSecret123!",
        "first_name": "Updated",
        "last_name": "User",
    }
    response = client.put(f"/users/{user.id}", json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["id"] == str(user.id)
    assert data["email"] == "updated@example.com"
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "User"
    assert data["company_id"] == str(company_id)


def test_put_user_not_found(client):
    """
    Test PUT /users/<id> for a non-existent user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    payload = {
        "email": "nouser@example.com",
        "password": "Secret123!",
        "first_name": "No",
        "last_name": "User",
    }
    response = client.put(f"/users/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert (
        "not found" in str(data).lower()
        or "error" in data
        or "message" in data
    )


def test_put_user_missing_required_fields(client, session):
    """
    Test PUT /users/<id> with missing required fields.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    user = User(
        email="miss@example.com",
        hashed_password="hash",
        first_name="Miss",
        last_name="Field",
        company_id=str(company_id),
    )
    session.add(user)
    session.commit()
    payload = {
        "email": "miss2@example.com"
        # missing password, first_name, last_name, company_id
    }
    response = client.put(f"/users/{user.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert (
        "password" in str(data).lower()
        or "first_name" in str(data).lower()
        or "last_name" in str(data).lower()
        or "company_id" in str(data).lower()
    )


##################################################
# Test cases for PATCH /users/<id>
##################################################


def test_patch_user_success(client, session):
    """
    Test PATCH /users/<id> for a partial update.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    user = User(
        email="patchme@example.com",
        hashed_password="oldhash",
        first_name="Patch",
        last_name="User",
        company_id=str(company_id),
    )
    session.add(user)
    session.commit()

    payload = {"first_name": "Patched", "last_name": "UserUpdated"}
    response = client.patch(f"/users/{user.id}", json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["first_name"] == "Patched"
    assert data["last_name"] == "UserUpdated"
    assert data["email"] == "patchme@example.com"


def test_patch_user_not_found(client):
    """
    Test PATCH /users/<id> for a non-existent user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    payload = {"first_name": "Ghost"}
    response = client.patch(f"/users/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert (
        "not found" in str(data).lower()
        or "error" in data
        or "message" in data
    )


def test_patch_user_invalid_email(client, session):
    """
    Test PATCH /users/<id> with invalid email format.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    user = User(
        email="patchmail@example.com",
        hashed_password="hash",
        first_name="PatchMail",
        last_name="User",
        company_id=str(company_id),
    )
    session.add(user)
    session.commit()
    payload = {"email": "not-an-email"}
    response = client.patch(f"/users/{user.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in str(data).lower()


##################################################
# Test cases for DELETE /users/<id>
##################################################


def test_delete_user_success(client, session):
    """
    Test DELETE /users/<id> for an existing user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    user = User(
        email="delete@example.com",
        hashed_password="hash",
        first_name="Del",
        last_name="User",
        company_id=str(company_id),
    )
    session.add(user)
    session.commit()

    response = client.delete(f"/users/{user.id}")
    assert response.status_code == 204

    # Vérifie que l'utilisateur n'existe plus
    get_response = client.get(f"/users/{user.id}")
    assert get_response.status_code == 404


def test_delete_user_not_found(client):
    """
    Test DELETE /users/<id> for a non-existent user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    response = client.delete(f"/users/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert (
        "not found" in str(data).lower()
        or "error" in data
        or "message" in data
    )


##################################################
# Test cases for GET /position/<string:position_id>/users
##################################################


def test_get_users_by_position(client, session):
    """
    Test GET /positions/<position_id>/users returns only users for the given position.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    position1_id = str(uuid.uuid4())
    position2_id = str(uuid.uuid4())

    user1 = User(
        email="pos1@example.com",
        hashed_password="hash",
        first_name="Pos1",
        last_name="User1",
        company_id=str(company_id),
        position_id=position1_id,
    )
    user2 = User(
        email="pos2@example.com",
        hashed_password="hash",
        first_name="Pos2",
        last_name="User2",
        company_id=str(company_id),
        position_id=position2_id,
    )
    user3 = User(
        email="nopos@example.com",
        hashed_password="hash",
        first_name="NoPos",
        last_name="User3",
        company_id=str(company_id),
        position_id=None,
    )
    session.add_all([user1, user2, user3])
    session.commit()

    response = client.get(f"/positions/{position1_id}/users")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["email"] == "pos1@example.com"

    response2 = client.get(f"/positions/{position2_id}/users")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, list)
    assert len(data2) == 1
    assert data2[0]["email"] == "pos2@example.com"


def test_get_users_by_position_not_found(client):
    """
    Test GET /positions/<position_id>/users for a position with no users.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_position_id = str(uuid.uuid4())
    response = client.get(f"/positions/{fake_position_id}/users")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


##################################################
# Test cases for POST /verify_password
##################################################


def test_verify_password_success(client, session):
    """
    Test POST /verify_password with correct email and password.
    Verify that last_login_at is updated on successful authentication.
    """
    company_id = str(uuid.uuid4())
    password = "MySecret123!"
    user = User(
        email="verify@example.com",
        hashed_password=generate_password_hash(password),
        first_name="Veri",
        last_name="Fy",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    # Store the initial last_login_at (should be None)
    initial_last_login = user.last_login_at
    assert initial_last_login is None

    payload = {"email": "verify@example.com", "password": password}
    response = client.post("/verify_password", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["email"] == "verify@example.com"

    # Verify last_login_at was updated
    session.refresh(user)
    assert user.last_login_at is not None
    assert data["last_login_at"] is not None


def test_verify_password_wrong_password(client, session):
    """
    Test POST /verify_password with wrong password.
    """
    company_id = str(uuid.uuid4())
    user = User(
        email="wrongpw@example.com",
        hashed_password=generate_password_hash("RightPassword!"),
        first_name="Wrong",
        last_name="PW",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    payload = {"email": "wrongpw@example.com", "password": "WrongPassword!"}
    response = client.post("/verify_password", json=payload)
    assert response.status_code == 403
    data = response.get_json()
    assert "invalid" in str(data).lower()


def test_verify_password_user_not_found(client):
    """
    Test POST /verify_password with non-existent user.
    """
    payload = {"email": "notfound@example.com", "password": "AnyPassword"}
    response = client.post("/verify_password", json=payload)
    assert response.status_code == 403
    data = response.get_json()
    assert "invalid" in str(data).lower()


def test_verify_password_missing_password(client, session):
    """
    Test POST /verify_password with missing password field.
    """
    company_id = str(uuid.uuid4())
    user = User(
        email="nopw@example.com",
        hashed_password=generate_password_hash("SomePassword!"),
        first_name="No",
        last_name="PW",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    payload = {"email": "nopw@example.com"}
    response = client.post("/verify_password", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "required" in str(data).lower()


##################################################
# Test cases for GET /users/<user_id>/roles
##################################################


@pytest.mark.skip(reason="Need refactor")
def test_get_user_roles_success(client):
    """
    Test GET /users/<user_id>/roles with successful response from Guardian service.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock the Guardian service response
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"roles": ["admin", "user", "editor"]}

    with mock.patch("requests.get", return_value=mock_response) as mock_get:
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/roles")

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == ["admin", "user", "editor"]

        # Verify the Guardian service was called correctly
        mock_get.assert_called_once_with(
            "http://guardian:8000/user-roles",
            params={"user_id": user_id},
            headers={"Cookie": f"access_token={jwt_token}"},
            timeout=5,
        )


def test_get_user_roles_missing_jwt(client):
    """
    Test GET /users/<user_id>/roles without JWT authentication.
    """
    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/users/{fake_user_id}/roles")
    assert response.status_code == 401
    data = response.get_json()
    assert "jwt" in str(data).lower() or "token" in str(data).lower()


def test_get_user_roles_missing_user_id_in_jwt(client):
    """
    Test GET /users/<user_id>/roles with JWT that doesn't contain user_id.
    """
    # Create a JWT without user_id
    jwt_secret = os.environ.get("JWT_SECRET", "test_secret")
    payload = {
        "company_id": str(uuid.uuid4())
        # Missing user_id
    }
    jwt_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/users/{fake_user_id}/roles")
    assert response.status_code == 401
    data = response.get_json()
    assert "missing user_id" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_roles_missing_guardian_url(client):
    """
    Test GET /users/<user_id>/roles when GUARDIAN_SERVICE_URL is not set.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Remove only GUARDIAN_SERVICE_URL from environment, keep JWT_SECRET
    current_env = dict(os.environ)
    jwt_secret = current_env.get("JWT_SECRET", "test_secret")
    with mock.patch.dict("os.environ", {"JWT_SECRET": jwt_secret}, clear=True):
        response = client.get(f"/users/{user_id}/roles")
        assert response.status_code == 500
        data = response.get_json()
        assert "internal server error" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_roles_guardian_request_exception(client):
    """
    Test GET /users/<user_id>/roles when Guardian service is unreachable.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock requests.get to raise an exception
    with mock.patch(
        "requests.get",
        side_effect=requests.exceptions.RequestException("Connection error"),
    ):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/roles")
            assert response.status_code == 500
            data = response.get_json()
            assert "error fetching roles" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_roles_guardian_non_200_response(client):
    """
    Test GET /users/<user_id>/roles when Guardian service returns non-200 status.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service to return 404
    mock_response = mock.Mock()
    mock_response.status_code = 404
    mock_response.text = "User not found in Guardian"

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/roles")
            assert response.status_code == 500
            data = response.get_json()
            assert "error fetching roles" in str(data).lower()


def test_get_user_roles_empty_roles(client):
    """
    Test GET /users/<user_id>/roles when Guardian returns empty roles.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service to return empty roles
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"roles": []}

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/roles")
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == []


def test_get_user_roles_guardian_response_missing_roles_key(client):
    """
    Test GET /users/<user_id>/roles when Guardian response doesn't contain 'roles' key.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response without 'roles' key
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "some other data"}

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/roles")
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == []  # Should default to empty list


def test_get_user_roles_user_not_found(client):
    """
    Test GET /users/<user_id>/roles when the requested user doesn't exist.
    """
    # Create test data for authentication
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to get roles for a non-existent user
    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/users/{fake_user_id}/roles")
    assert response.status_code == 404
    data = response.get_json()
    assert "user not found" in str(data).lower()


def test_get_user_roles_different_company_access_denied(client, session):
    """
    Test GET /users/<user_id>/roles when trying to access a user from a different company.
    """
    # Create first company and user
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company1_id = resp.get_json()["company"]["id"]
    user1_id = resp.get_json()["user"]["id"]

    # Create a second user in a different company
    company2_id = str(uuid.uuid4())
    user2 = User(
        email="user2@company2.com",
        hashed_password="hashedpw",
        first_name="User",
        last_name="Two",
        company_id=company2_id,
    )
    session.add(user2)
    session.commit()

    # Authenticate as user1 and try to access user2's roles
    jwt_token = create_jwt_token(company1_id, user1_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get(f"/users/{user2.id}/roles")
    assert response.status_code == 403
    data = response.get_json()
    assert "access denied" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_roles_same_company_allowed(client, session):
    """
    Test GET /users/<user_id>/roles when accessing a user from the same company.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user1_id = resp.get_json()["user"]["id"]

    # Create a second user in the same company
    user2 = User(
        email="user2@company.com",
        hashed_password="hashedpw",
        first_name="User",
        last_name="Two",
        company_id=company_id,
    )
    session.add(user2)
    session.commit()

    # Authenticate as user1 and try to access user2's roles
    jwt_token = create_jwt_token(company_id, user1_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"roles": ["viewer"]}

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user2.id}/roles")
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert data["roles"] == ["viewer"]


##################################################
# Test cases for POST /users/<user_id>/roles
##################################################


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_success(client):
    """
    Test POST /users/<user_id>/roles with successful role assignment.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response for successful role assignment
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
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            payload = {"role_id": mock_role_id}
            response = client.post(f"/users/{user_id}/roles", json=payload)

            # Verify the response
            assert response.status_code == 201
            data = response.get_json()
            assert "id" in data
            assert "user_id" in data
            assert "role_id" in data
            assert data["id"] == mock_user_role_id
            assert data["user_id"] == user_id
            assert data["role_id"] == mock_role_id

            # Verify the Guardian service was called correctly
            mock_post.assert_called_once_with(
                "http://guardian:8000/user-roles",
                json={"user_id": user_id, "role_id": mock_role_id},
                headers={"Cookie": f"access_token={jwt_token}"},
                timeout=5,
            )


def test_post_user_role_missing_jwt(client):
    """
    Test POST /users/<user_id>/roles without JWT authentication.
    """
    fake_user_id = str(uuid.uuid4())
    payload = {"role": "admin"}
    response = client.post(f"/users/{fake_user_id}/roles", json=payload)
    assert response.status_code == 401
    data = response.get_json()
    assert "jwt" in str(data).lower() or "token" in str(data).lower()


def test_post_user_role_missing_user_id_in_jwt(client):
    """
    Test POST /users/<user_id>/roles with JWT that doesn't contain user_id.
    """
    # Create a JWT without user_id
    jwt_secret = os.environ.get("JWT_SECRET", "test_secret")
    payload = {
        "company_id": str(uuid.uuid4())
        # Missing user_id
    }
    jwt_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_user_id = str(uuid.uuid4())
    role_payload = {"role": "admin"}
    response = client.post(f"/users/{fake_user_id}/roles", json=role_payload)
    assert response.status_code == 401
    data = response.get_json()
    assert "missing user_id" in str(data).lower()


def test_post_user_role_user_not_found(client):
    """
    Test POST /users/<user_id>/roles when the target user doesn't exist.
    """
    # Create test data for authentication
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to assign role to non-existent user
    fake_user_id = str(uuid.uuid4())
    payload = {"role": "admin"}
    response = client.post(f"/users/{fake_user_id}/roles", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "user not found" in str(data).lower()


def test_post_user_role_different_company_access_denied(client, session):
    """
    Test POST /users/<user_id>/roles when trying to assign role to user from different company.
    """
    # Create first company and user
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company1_id = resp.get_json()["company"]["id"]
    user1_id = resp.get_json()["user"]["id"]

    # Create a second user in a different company
    company2_id = str(uuid.uuid4())
    user2 = User(
        email="user2@company2.com",
        hashed_password="hashedpw",
        first_name="User",
        last_name="Two",
        company_id=company2_id,
    )
    session.add(user2)
    session.commit()

    # Authenticate as user1 and try to assign role to user2
    jwt_token = create_jwt_token(company1_id, user1_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"role": "admin"}
    response = client.post(f"/users/{user2.id}/roles", json=payload)
    assert response.status_code == 403
    data = response.get_json()
    assert "access denied" in str(data).lower()


def test_post_user_role_missing_json_data(client):
    """
    Test POST /users/<user_id>/roles without JSON payload.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.post(f"/users/{user_id}/roles")
    assert response.status_code == 400
    data = response.get_json()
    assert "json data required" in str(data).lower()


def test_post_user_role_missing_role_field(client):
    """
    Test POST /users/<user_id>/roles with JSON payload missing 'role' field.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"other_field": "value"}  # Missing 'role' or 'role_id' field
    response = client.post(f"/users/{user_id}/roles", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "role id field is required" in str(data).lower()


def test_post_user_role_invalid_role_format(client):
    """
    Test POST /users/<user_id>/roles with invalid role format.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Test empty string
    payload = {"role_id": ""}
    response = client.post(f"/users/{user_id}/roles", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "role id field is required" in str(data).lower()

    # Test whitespace only
    payload = {"role_id": "   "}
    response = client.post(f"/users/{user_id}/roles", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "role id must be a non-empty string" in str(data).lower()

    # Test non-string value
    payload = {"role_id": 123}
    response = client.post(f"/users/{user_id}/roles", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "role id must be a non-empty string" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_missing_guardian_url(client):
    """
    Test POST /users/<user_id>/roles when GUARDIAN_SERVICE_URL is not set.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Remove only GUARDIAN_SERVICE_URL from environment, keep JWT_SECRET
    current_env = dict(os.environ)
    jwt_secret = current_env.get("JWT_SECRET", "test_secret")
    with mock.patch.dict("os.environ", {"JWT_SECRET": jwt_secret}, clear=True):
        payload = {"role": "admin"}
        response = client.post(f"/users/{user_id}/roles", json=payload)
        assert response.status_code == 500
        data = response.get_json()
        assert "internal server error" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_guardian_request_exception(client):
    """
    Test POST /users/<user_id>/roles when Guardian service is unreachable.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock requests.post to raise an exception
    with mock.patch(
        "requests.post",
        side_effect=requests.exceptions.RequestException("Connection error"),
    ):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            payload = {"role": "admin"}
            response = client.post(f"/users/{user_id}/roles", json=payload)
            assert response.status_code == 500
            data = response.get_json()
            assert "error assigning role" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_guardian_conflict_response(client):
    """
    Test POST /users/<user_id>/roles when Guardian returns 409 (role already exists).
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service to return 409 (conflict)
    mock_response = mock.Mock()
    mock_response.status_code = 409

    with mock.patch("requests.post", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            payload = {"role": "admin"}
            response = client.post(f"/users/{user_id}/roles", json=payload)
            assert response.status_code == 409
            data = response.get_json()
            assert "already assigned" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_guardian_bad_request_response(client):
    """
    Test POST /users/<user_id>/roles when Guardian returns 400 (bad request).
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service to return 400 (bad request)
    mock_response = mock.Mock()
    mock_response.status_code = 400
    mock_response.text = "Invalid role format"

    with mock.patch("requests.post", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            payload = {"role": "invalid_role"}
            response = client.post(f"/users/{user_id}/roles", json=payload)
            assert response.status_code == 400
            data = response.get_json()
            assert "invalid role" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_guardian_server_error(client):
    """
    Test POST /users/<user_id>/roles when Guardian returns 500 (server error).
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service to return 500 (server error)
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"

    with mock.patch("requests.post", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            payload = {"role": "admin"}
            response = client.post(f"/users/{user_id}/roles", json=payload)
            assert response.status_code == 500
            data = response.get_json()
            assert "error assigning role" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_same_company_allowed(client, session):
    """
    Test POST /users/<user_id>/roles when assigning role to user in the same company.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user1_id = resp.get_json()["user"]["id"]

    # Create a second user in the same company
    user2 = User(
        email="user2@company.com",
        hashed_password="hashedpw",
        first_name="User",
        last_name="Two",
        company_id=company_id,
    )
    session.add(user2)
    session.commit()

    # Authenticate as user1 and assign role to user2
    jwt_token = create_jwt_token(company_id, user1_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response
    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = str(uuid.uuid4())
    mock_response = mock.Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": str(user2.id),
        "role_id": mock_role_id,
    }

    with mock.patch("requests.post", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            payload = {"role_id": mock_role_id}
            response = client.post(f"/users/{user2.id}/roles", json=payload)
            assert response.status_code == 201
            data = response.get_json()
            assert "id" in data
            assert "user_id" in data
            assert "role_id" in data
            assert data["id"] == mock_user_role_id
            assert data["user_id"] == str(user2.id)
            assert data["role_id"] == mock_role_id


@pytest.mark.skip(reason="Need refactor")
def test_post_user_role_backward_compatibility(client):
    """
    Test POST /users/<user_id>/roles with 'role' field for backward compatibility.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response for successful role assignment
    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = (
        "admin_role_name"  # Using role name for backward compatibility
    )
    mock_response = mock.Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": user_id,
        "role_id": mock_role_id,
    }

    with mock.patch("requests.post", return_value=mock_response) as mock_post:
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            # Test with 'role' field instead of 'role_id'
            payload = {"role": mock_role_id}
            response = client.post(f"/users/{user_id}/roles", json=payload)

            # Verify the response
            assert response.status_code == 201
            data = response.get_json()
            assert "id" in data
            assert "user_id" in data
            assert "role_id" in data
            assert data["id"] == mock_user_role_id
            assert data["user_id"] == user_id
            assert data["role_id"] == mock_role_id

            # Verify the Guardian service was called correctly with role_id
            mock_post.assert_called_once_with(
                "http://guardian:8000/user-roles",
                json={"user_id": user_id, "role_id": mock_role_id},
                headers={"Cookie": f"access_token={jwt_token}"},
                timeout=5,
            )


# =============================================================================
# UserRolesResource (Individual Role) Tests
# =============================================================================


@pytest.mark.skip(reason="Need refactor")
def test_get_user_role_success(client):
    """
    Test GET /users/<user_id>/roles/<user_role_id> with successful retrieval.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response
    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = str(uuid.uuid4())
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": user_id,
        "role_id": mock_role_id,
    }

    with mock.patch("requests.get", return_value=mock_response) as mock_get:
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(
                f"/users/{user_id}/roles/{mock_user_role_id}"
            )

            # Verify the response
            assert response.status_code == 200
            data = response.get_json()
            assert data["id"] == mock_user_role_id
            assert data["user_id"] == user_id
            assert data["role_id"] == mock_role_id

            # Verify the Guardian service was called correctly
            mock_get.assert_called_once_with(
                f"http://guardian:8000/user-roles/{mock_user_role_id}",
                headers={"Cookie": f"access_token={jwt_token}"},
                timeout=5,
            )


def test_get_user_role_missing_jwt(client):
    """
    Test GET /users/<user_id>/roles/<user_role_id> without JWT authentication.
    """
    user_id = str(uuid.uuid4())
    user_role_id = str(uuid.uuid4())

    response = client.get(f"/users/{user_id}/roles/{user_role_id}")
    assert response.status_code == 401
    data = response.get_json()
    assert "jwt token" in str(data).lower()


def test_get_user_role_user_not_found(client):
    """
    Test GET /users/<user_id>/roles/<user_role_id> when user doesn't exist.
    """
    # Create test data for authentication
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    auth_user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, auth_user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to access role for non-existent user
    non_existent_user_id = str(uuid.uuid4())
    user_role_id = str(uuid.uuid4())

    response = client.get(
        f"/users/{non_existent_user_id}/roles/{user_role_id}"
    )
    assert response.status_code == 404
    data = response.get_json()
    assert (
        "not found" in str(data).lower()
        or "access denied" in str(data).lower()
    )


@pytest.mark.skip(reason="Need refactor")
def test_get_user_role_not_found(client):
    """
    Test GET /users/<user_id>/roles/<user_role_id> when role assignment doesn't exist.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service 404 response
    mock_response = mock.Mock()
    mock_response.status_code = 404

    user_role_id = str(uuid.uuid4())

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/roles/{user_role_id}")

            assert response.status_code == 404
            data = response.get_json()
            assert "not found" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_role_wrong_user(client):
    """
    Test GET /users/<user_id>/roles/<user_role_id> when role belongs to different user.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response with different user_id
    other_user_id = str(uuid.uuid4())
    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = str(uuid.uuid4())
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": other_user_id,  # Different user
        "role_id": mock_role_id,
    }

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(
                f"/users/{user_id}/roles/{mock_user_role_id}"
            )

            assert response.status_code == 404
            data = response.get_json()
            assert "not found" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_delete_user_role_success(client):
    """
    Test DELETE /users/<user_id>/roles/<user_role_id> with successful deletion.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service responses
    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = str(uuid.uuid4())

    # Mock GET response (to verify role exists)
    mock_get_response = mock.Mock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": user_id,
        "role_id": mock_role_id,
    }

    # Mock DELETE response
    mock_delete_response = mock.Mock()
    mock_delete_response.status_code = 204

    with mock.patch(
        "requests.get", return_value=mock_get_response
    ) as mock_get:
        with mock.patch(
            "requests.delete", return_value=mock_delete_response
        ) as mock_delete:
            with mock.patch.dict(
                "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
            ):
                response = client.delete(
                    f"/users/{user_id}/roles/{mock_user_role_id}"
                )

                # Verify the response
                assert response.status_code == 204

                # Verify the Guardian service was called correctly
                mock_get.assert_called_once_with(
                    f"http://guardian:8000/user-roles/{mock_user_role_id}",
                    headers={"Cookie": f"access_token={jwt_token}"},
                    timeout=5,
                )
                mock_delete.assert_called_once_with(
                    f"http://guardian:8000/user-roles/{mock_user_role_id}",
                    headers={"Cookie": f"access_token={jwt_token}"},
                    timeout=5,
                )


def test_delete_user_role_missing_jwt(client):
    """
    Test DELETE /users/<user_id>/roles/<user_role_id> without JWT authentication.
    """
    user_id = str(uuid.uuid4())
    user_role_id = str(uuid.uuid4())

    response = client.delete(f"/users/{user_id}/roles/{user_role_id}")
    assert response.status_code == 401
    data = response.get_json()
    assert "jwt token" in str(data).lower()


def test_delete_user_role_user_not_found(client):
    """
    Test DELETE /users/<user_id>/roles/<user_role_id> when user doesn't exist.
    """
    # Create test data for authentication
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    auth_user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, auth_user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to delete role for non-existent user
    non_existent_user_id = str(uuid.uuid4())
    user_role_id = str(uuid.uuid4())

    response = client.delete(
        f"/users/{non_existent_user_id}/roles/{user_role_id}"
    )
    assert response.status_code == 404
    data = response.get_json()
    assert (
        "not found" in str(data).lower()
        or "access denied" in str(data).lower()
    )


@pytest.mark.skip(reason="Need refactor")
def test_delete_user_role_not_found(client):
    """
    Test DELETE /users/<user_id>/roles/<user_role_id> when role assignment doesn't exist.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service 404 response for GET
    mock_response = mock.Mock()
    mock_response.status_code = 404

    user_role_id = str(uuid.uuid4())

    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.delete(f"/users/{user_id}/roles/{user_role_id}")

            assert response.status_code == 404
            data = response.get_json()
            assert "not found" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_delete_user_role_wrong_user(client):
    """
    Test DELETE /users/<user_id>/roles/<user_role_id> when role belongs to different user.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response with different user_id
    other_user_id = str(uuid.uuid4())
    mock_user_role_id = str(uuid.uuid4())
    mock_role_id = str(uuid.uuid4())
    mock_get_response = mock.Mock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        "id": mock_user_role_id,
        "user_id": other_user_id,  # Different user
        "role_id": mock_role_id,
    }

    with mock.patch("requests.get", return_value=mock_get_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.delete(
                f"/users/{user_id}/roles/{mock_user_role_id}"
            )

            assert response.status_code == 404
            data = response.get_json()
            assert "not found" in str(data).lower()


##################################################
# Test cases for GET /users/<user_id>/policies
##################################################
@pytest.mark.skip(reason="Need refactor")
def test_get_user_policies_success(client):
    """
    Test GET /users/<user_id>/policies with successful response from Guardian.
    Should fetch roles then policies for each role.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock user roles response
    role_id_1 = str(uuid.uuid4())
    role_id_2 = str(uuid.uuid4())
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_1},
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_2},
    ]

    # Mock policies for role 1
    policy_1 = {"id": str(uuid.uuid4()), "name": "policy1"}
    policy_2 = {"id": str(uuid.uuid4()), "name": "policy2"}
    policies_response_1 = mock.Mock()
    policies_response_1.status_code = 200
    policies_response_1.json.return_value = [policy_1, policy_2]

    # Mock policies for role 2
    policy_3 = {"id": str(uuid.uuid4()), "name": "policy3"}
    policies_response_2 = mock.Mock()
    policies_response_2.status_code = 200
    policies_response_2.json.return_value = [
        policy_3,
        policy_1,
    ]  # policy_1 duplicated

    def mock_get_side_effect(url, **kwargs):
        if "/user-roles" in url:
            return roles_response
        if f"/roles/{role_id_1}/policies" in url:
            return policies_response_1
        if f"/roles/{role_id_2}/policies" in url:
            return policies_response_2
        raise ValueError(f"Unexpected URL: {url}")

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/policies")

            assert response.status_code == 200
            data = response.get_json()
            assert "policies" in data
            # Should have 3 unique policies (policy_1 deduplicated)
            assert len(data["policies"]) == 3
            policy_ids = [p["id"] for p in data["policies"]]
            assert policy_1["id"] in policy_ids
            assert policy_2["id"] in policy_ids
            assert policy_3["id"] in policy_ids


def test_get_user_policies_no_roles(client):
    """
    Test GET /users/<user_id>/policies when user has no roles.
    Should return empty policies list.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock empty roles response
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = []

    with mock.patch("requests.get", return_value=roles_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/policies")

            assert response.status_code == 200
            data = response.get_json()
            assert "policies" in data
            assert data["policies"] == []


def test_get_user_policies_missing_jwt(client):
    """
    Test GET /users/<user_id>/policies without JWT authentication.
    """
    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/users/{fake_user_id}/policies")
    assert response.status_code == 401


def test_get_user_policies_user_not_found(client):
    """
    Test GET /users/<user_id>/policies with non-existent user.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/users/{fake_user_id}/policies")
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower()


def test_get_user_policies_different_company_denied(client, session):
    """
    Test GET /users/<user_id>/policies when accessing user from different company.
    """
    # Create first user
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id_1 = resp.get_json()["company"]["id"]
    user_id_1 = resp.get_json()["user"]["id"]

    # Create second user in different company
    other_company_id = str(uuid.uuid4())
    other_user = User(
        email="other@example.com",
        hashed_password=generate_password_hash("password"),
        first_name="Other",
        last_name="User",
        company_id=other_company_id,
    )
    session.add(other_user)
    session.commit()

    # Authenticate as first user
    jwt_token = create_jwt_token(company_id_1, user_id_1)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to access second user's policies
    response = client.get(f"/users/{other_user.id}/policies")
    assert response.status_code == 403
    data = response.get_json()
    assert "denied" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_policies_missing_guardian_url(client):
    """
    Test GET /users/<user_id>/policies when GUARDIAN_SERVICE_URL is not set.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Keep JWT_SECRET but remove GUARDIAN_SERVICE_URL
    jwt_secret = os.environ.get("JWT_SECRET", "test_secret")
    with mock.patch.dict("os.environ", {"JWT_SECRET": jwt_secret}, clear=True):
        response = client.get(f"/users/{user_id}/policies")
        assert response.status_code == 500


@pytest.mark.skip(reason="Need refactor")
def test_get_user_policies_guardian_roles_error(client):
    """
    Test GET /users/<user_id>/policies when Guardian fails to return roles.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian returning error for roles
    roles_response = mock.Mock()
    roles_response.status_code = 500
    roles_response.text = "Internal server error"

    with mock.patch("requests.get", return_value=roles_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/policies")
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_policies_guardian_policies_partial_failure(client):
    """
    Test GET /users/<user_id>/policies when some role policies fail.
    Should continue with other roles and return partial results.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    role_id_1 = str(uuid.uuid4())
    role_id_2 = str(uuid.uuid4())
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_1},
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_2},
    ]

    # Role 1 policies succeed
    policy_1 = {"id": str(uuid.uuid4()), "name": "policy1"}
    policies_response_1 = mock.Mock()
    policies_response_1.status_code = 200
    policies_response_1.json.return_value = [policy_1]

    # Role 2 policies fail
    policies_response_2 = mock.Mock()
    policies_response_2.status_code = 500
    policies_response_2.text = "Error"

    def mock_get_side_effect(url, **kwargs):
        if "/user-roles" in url:
            return roles_response
        if f"/roles/{role_id_1}/policies" in url:
            return policies_response_1
        if f"/roles/{role_id_2}/policies" in url:
            return policies_response_2
        raise ValueError(f"Unexpected URL: {url}")

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/policies")

            # Should still succeed with partial results
            assert response.status_code == 200
            data = response.get_json()
            assert "policies" in data
            assert len(data["policies"]) == 1
            assert data["policies"][0]["id"] == policy_1["id"]


def test_get_user_policies_role_not_found_in_guardian(client):
    """
    Test GET /users/<user_id>/policies when a role is not found in Guardian.
    Should skip that role and continue.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    role_id_1 = str(uuid.uuid4())
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_1},
    ]

    # Role not found in Guardian
    policies_response = mock.Mock()
    policies_response.status_code = 404

    def mock_get_side_effect(url, **kwargs):
        if "/user-roles" in url:
            return roles_response
        if f"/roles/{role_id_1}/policies" in url:
            return policies_response
        raise ValueError(f"Unexpected URL: {url}")

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/policies")

            # Should succeed with empty policies
            assert response.status_code == 200
            data = response.get_json()
            assert "policies" in data
            assert data["policies"] == []


##################################################
# User Permissions Tests
##################################################
@pytest.mark.skip(reason="Need refactor")
def test_get_user_permissions_success(client):
    """
    Test GET /users/<user_id>/permissions with successful response from Guardian.
    Should fetch roles, then policies for each role, then permissions for each policy.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock user roles response
    role_id_1 = str(uuid.uuid4())
    role_id_2 = str(uuid.uuid4())
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_1},
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_2},
    ]

    # Mock policies for role 1
    policy_id_1 = str(uuid.uuid4())
    policy_id_2 = str(uuid.uuid4())
    policies_response_1 = mock.Mock()
    policies_response_1.status_code = 200
    policies_response_1.json.return_value = [
        {"id": policy_id_1, "name": "policy1"},
        {"id": policy_id_2, "name": "policy2"},
    ]

    # Mock policies for role 2
    policy_id_3 = str(uuid.uuid4())
    policies_response_2 = mock.Mock()
    policies_response_2.status_code = 200
    policies_response_2.json.return_value = [
        {"id": policy_id_3, "name": "policy3"},
        {"id": policy_id_1, "name": "policy1"},  # policy_id_1 duplicated
    ]

    # Mock permissions for policy 1
    permission_1 = {
        "id": str(uuid.uuid4()),
        "service": "identity",
        "resource_name": "user",
    }
    permission_2 = {
        "id": str(uuid.uuid4()),
        "service": "identity",
        "resource_name": "company",
    }
    permissions_response_1 = mock.Mock()
    permissions_response_1.status_code = 200
    permissions_response_1.json.return_value = [permission_1, permission_2]

    # Mock permissions for policy 2
    permission_3 = {
        "id": str(uuid.uuid4()),
        "service": "guardian",
        "resource_name": "role",
    }
    permissions_response_2 = mock.Mock()
    permissions_response_2.status_code = 200
    permissions_response_2.json.return_value = [
        permission_3,
        permission_1,
    ]  # permission_1 duplicated

    # Mock permissions for policy 3
    permission_4 = {
        "id": str(uuid.uuid4()),
        "service": "guardian",
        "resource_name": "policy",
    }
    permissions_response_3 = mock.Mock()
    permissions_response_3.status_code = 200
    permissions_response_3.json.return_value = [permission_4]

    def mock_get_side_effect(url, **kwargs):
        if "/user-roles" in url:
            return roles_response
        if f"/roles/{role_id_1}/policies" in url:
            return policies_response_1
        if f"/roles/{role_id_2}/policies" in url:
            return policies_response_2
        if f"/policies/{policy_id_1}/permissions" in url:
            return permissions_response_1
        if f"/policies/{policy_id_2}/permissions" in url:
            return permissions_response_2
        if f"/policies/{policy_id_3}/permissions" in url:
            return permissions_response_3
        raise ValueError(f"Unexpected URL: {url}")

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/permissions")

            assert response.status_code == 200
            data = response.get_json()
            assert "permissions" in data
            # Should have 4 unique permissions (permission_1 deduplicated)
            assert len(data["permissions"]) == 4
            permission_ids = [p["id"] for p in data["permissions"]]
            assert permission_1["id"] in permission_ids
            assert permission_2["id"] in permission_ids
            assert permission_3["id"] in permission_ids
            assert permission_4["id"] in permission_ids


def test_get_user_permissions_no_roles(client):
    """
    Test GET /users/<user_id>/permissions when user has no roles.
    Should return empty permissions list.
    """
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock empty roles response
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = []

    with mock.patch("requests.get", return_value=roles_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/permissions")

            assert response.status_code == 200
            data = response.get_json()
            assert "permissions" in data
            assert data["permissions"] == []


def test_get_user_permissions_missing_jwt(client):
    """
    Test GET /users/<user_id>/permissions without JWT authentication.
    """
    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/users/{fake_user_id}/permissions")
    assert response.status_code == 401


def test_get_user_permissions_user_not_found(client):
    """
    Test GET /users/<user_id>/permissions with non-existent user.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/users/{fake_user_id}/permissions")
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower()


def test_get_user_permissions_different_company_denied(client, session):
    """
    Test GET /users/<user_id>/permissions when accessing user from different company.
    """
    # Create first user
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id_1 = resp.get_json()["company"]["id"]
    user_id_1 = resp.get_json()["user"]["id"]

    # Create second user in different company
    other_company_id = str(uuid.uuid4())
    other_user = User(
        email="other@example.com",
        hashed_password=generate_password_hash("password"),
        first_name="Other",
        last_name="User",
        company_id=other_company_id,
    )
    session.add(other_user)
    session.commit()

    # Authenticate as first user
    jwt_token = create_jwt_token(company_id_1, user_id_1)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Try to access second user's permissions
    response = client.get(f"/users/{other_user.id}/permissions")
    assert response.status_code == 403
    data = response.get_json()
    assert "denied" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_permissions_missing_guardian_url(client):
    """
    Test GET /users/<user_id>/permissions when GUARDIAN_SERVICE_URL is not set.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Keep JWT_SECRET but remove GUARDIAN_SERVICE_URL
    jwt_secret = os.environ.get("JWT_SECRET", "test_secret")
    with mock.patch.dict("os.environ", {"JWT_SECRET": jwt_secret}, clear=True):
        response = client.get(f"/users/{user_id}/permissions")
        assert response.status_code == 500


@pytest.mark.skip(reason="Need refactor")
def test_get_user_permissions_guardian_roles_error(client):
    """
    Test GET /users/<user_id>/permissions when Guardian fails to return roles.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian returning error for roles
    roles_response = mock.Mock()
    roles_response.status_code = 500
    roles_response.text = "Internal server error"

    with mock.patch("requests.get", return_value=roles_response):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/permissions")
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in str(data).lower()


@pytest.mark.skip(reason="Need refactor")
def test_get_user_permissions_guardian_permissions_partial_failure(client):
    """
    Test GET /users/<user_id>/permissions when some policy permissions fail.
    Should continue with other policies and return partial results.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    role_id_1 = str(uuid.uuid4())
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_1},
    ]

    # Mock policies
    policy_id_1 = str(uuid.uuid4())
    policy_id_2 = str(uuid.uuid4())
    policies_response = mock.Mock()
    policies_response.status_code = 200
    policies_response.json.return_value = [
        {"id": policy_id_1, "name": "policy1"},
        {"id": policy_id_2, "name": "policy2"},
    ]

    # Policy 1 permissions succeed
    permission_1 = {
        "id": str(uuid.uuid4()),
        "service": "identity",
        "resource_name": "user",
    }
    permissions_response_1 = mock.Mock()
    permissions_response_1.status_code = 200
    permissions_response_1.json.return_value = [permission_1]

    # Policy 2 permissions fail
    permissions_response_2 = mock.Mock()
    permissions_response_2.status_code = 500
    permissions_response_2.text = "Error"

    def mock_get_side_effect(url, **kwargs):
        if "/user-roles" in url:
            return roles_response
        if f"/roles/{role_id_1}/policies" in url:
            return policies_response
        if f"/policies/{policy_id_1}/permissions" in url:
            return permissions_response_1
        if f"/policies/{policy_id_2}/permissions" in url:
            return permissions_response_2
        raise ValueError(f"Unexpected URL: {url}")

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/permissions")

            # Should still succeed with partial results
            assert response.status_code == 200
            data = response.get_json()
            assert "permissions" in data
            assert len(data["permissions"]) == 1
            assert data["permissions"][0]["id"] == permission_1["id"]


def test_get_user_permissions_policy_not_found_in_guardian(client):
    """
    Test GET /users/<user_id>/permissions when a policy is not found in Guardian.
    Should skip that policy and continue.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    role_id_1 = str(uuid.uuid4())
    roles_response = mock.Mock()
    roles_response.status_code = 200
    roles_response.json.return_value = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": role_id_1},
    ]

    # Mock policies
    policy_id_1 = str(uuid.uuid4())
    policies_response = mock.Mock()
    policies_response.status_code = 200
    policies_response.json.return_value = [
        {"id": policy_id_1, "name": "policy1"},
    ]

    # Policy not found in Guardian
    permissions_response = mock.Mock()
    permissions_response.status_code = 404

    def mock_get_side_effect(url, **kwargs):
        if "/user-roles" in url:
            return roles_response
        if f"/roles/{role_id_1}/policies" in url:
            return policies_response
        if f"/policies/{policy_id_1}/permissions" in url:
            return permissions_response
        raise ValueError(f"Unexpected URL: {url}")

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:8000"}
        ):
            response = client.get(f"/users/{user_id}/permissions")

            # Should succeed with empty permissions
            assert response.status_code == 200
            data = response.get_json()
            assert "permissions" in data
            assert data["permissions"] == []
