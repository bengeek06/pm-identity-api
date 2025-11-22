"""
Unit tests for password reset functionality (Issue #12 Phase 1).

Tests admin-initiated password reset and user password change endpoints.
"""

# pylint: disable=unused-argument

import uuid
from unittest import mock

from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User
from tests.unit.conftest import create_jwt_token

##################################################
# Test cases for POST /users/{id}/admin-reset-password
##################################################


def test_admin_reset_password_success(client, session):
    """Test successful admin password reset."""
    company_id = str(uuid.uuid4())

    # Create user to reset
    user = User(
        email="user@example.com",
        hashed_password=generate_password_hash("OldPassword123"),
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    # Authenticate as admin from same company
    jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    with mock.patch(
        "app.resources.user_password.check_access_required"
    ) as mock_guardian:
        mock_guardian.return_value = lambda f: f

        response = client.post(f"/users/{user.id}/admin-reset-password")

        assert response.status_code == 200
        data = response.get_json()
        assert "temporary_password" in data
        assert len(data["temporary_password"]) == 12
        assert data["message"] == "Password reset successful"

        # Verify user has password_reset_required flag set
        session.refresh(user)
        assert user.password_reset_required is True
        assert user.last_password_change is not None

        # Verify password was actually changed
        assert check_password_hash(
            user.hashed_password, data["temporary_password"]
        )


def test_admin_reset_password_user_not_found(client, session):
    """Test admin reset with non-existent user ID."""
    company_id = str(uuid.uuid4())

    jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_user_id = str(uuid.uuid4())
    response = client.post(f"/users/{fake_user_id}/admin-reset-password")

    assert response.status_code == 404
    assert "not found" in response.get_json()["message"].lower()


def test_admin_reset_password_different_company(client, session):
    """Test admin cannot reset password for user in different company."""
    company_id_1 = str(uuid.uuid4())
    company_id_2 = str(uuid.uuid4())

    # Create user in company 1
    user = User(
        email="user@company1.com",
        hashed_password=generate_password_hash("OldPassword123"),
        first_name="Test",
        last_name="User",
        company_id=company_id_1,
    )
    session.add(user)
    session.commit()

    # Authenticate as admin from company 2
    jwt_token = create_jwt_token(company_id_2, str(uuid.uuid4()))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.post(f"/users/{user.id}/admin-reset-password")

    assert response.status_code == 403
    assert "different company" in response.get_json()["message"].lower()


def test_admin_reset_password_without_auth(client, session):
    """Test admin reset without authentication fails."""
    user_id = str(uuid.uuid4())
    response = client.post(f"/users/{user_id}/admin-reset-password")

    # Should fail without JWT
    assert response.status_code in [401, 403]


def test_admin_reset_password_guardian_disabled(client, session):
    """Test admin reset when Guardian is disabled (test environment)."""
    # In test environment, Guardian is disabled and bypassed
    # This test verifies that the endpoint still works with bypass
    company_id = str(uuid.uuid4())

    user = User(
        email="user@example.com",
        hashed_password=generate_password_hash("OldPassword123"),
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.post(f"/users/{user.id}/admin-reset-password")

    # Should succeed when Guardian is disabled (test environment)
    assert response.status_code == 200


##################################################
# Test cases for PATCH /users/me/change-password
##################################################


def test_user_change_password_success(client, session):
    """Test successful user password change."""
    company_id = str(uuid.uuid4())
    old_password = "OldPassword123"

    user = User(
        email="user@example.com",
        hashed_password=generate_password_hash(old_password),
        first_name="Test",
        last_name="User",
        company_id=company_id,
        password_reset_required=True,
    )
    session.add(user)
    session.commit()

    jwt_token = create_jwt_token(company_id, str(user.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    new_password = "NewSecurePassword456"
    response = client.patch(
        "/users/me/change-password",
        json={
            "current_password": old_password,
            "new_password": new_password,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Password changed successfully"

    # Verify password was changed
    session.refresh(user)
    assert check_password_hash(user.hashed_password, new_password)

    # Verify password_reset_required flag was cleared
    assert user.password_reset_required is False
    assert user.last_password_change is not None


def test_user_change_password_wrong_current_password(client, session):
    """Test password change with wrong current password."""
    company_id = str(uuid.uuid4())

    user = User(
        email="user@example.com",
        hashed_password=generate_password_hash("RealPassword123"),
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    jwt_token = create_jwt_token(company_id, str(user.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.patch(
        "/users/me/change-password",
        json={
            "current_password": "WrongPassword456",
            "new_password": "NewPassword789",
        },
    )

    assert response.status_code == 400
    assert (
        "current password is incorrect"
        in response.get_json()["message"].lower()
    )


def test_user_change_password_too_short(client, session):
    """Test password change with new password too short."""
    company_id = str(uuid.uuid4())
    old_password = "OldPassword123"

    user = User(
        email="user@example.com",
        hashed_password=generate_password_hash(old_password),
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    jwt_token = create_jwt_token(company_id, str(user.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.patch(
        "/users/me/change-password",
        json={
            "current_password": old_password,
            "new_password": "short",
        },
    )

    assert response.status_code == 400
    assert "at least 8 characters" in response.get_json()["message"].lower()


def test_user_change_password_missing_fields(client, session):
    """Test password change with missing required fields."""
    company_id = str(uuid.uuid4())

    user = User(
        email="user@example.com",
        hashed_password=generate_password_hash("OldPassword123"),
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    jwt_token = create_jwt_token(company_id, str(user.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Missing new_password
    response = client.patch(
        "/users/me/change-password",
        json={"current_password": "OldPassword123"},
    )

    assert response.status_code == 400


def test_user_change_password_no_data(client, session):
    """Test password change with no data provided."""
    company_id = str(uuid.uuid4())

    user = User(
        email="user@example.com",
        hashed_password=generate_password_hash("OldPassword123"),
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    jwt_token = create_jwt_token(company_id, str(user.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.patch("/users/me/change-password")

    assert response.status_code in [
        400,
        415,
    ]  # Bad Request or Unsupported Media Type


def test_user_change_password_without_auth(client, session):
    """Test password change without authentication fails."""
    response = client.patch(
        "/users/me/change-password",
        json={
            "current_password": "old",
            "new_password": "new_password",
        },
    )

    # Should fail without JWT
    assert response.status_code in [401, 403]


##################################################
# Test cases for password reset fields
##################################################


def test_user_default_password_reset_required(session):
    """Test that password_reset_required defaults to False."""
    company_id = str(uuid.uuid4())
    user = User(
        email="test@example.com",
        hashed_password="hash",
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    assert user.password_reset_required is False


def test_user_last_password_change_nullable(session):
    """Test that last_password_change can be NULL."""
    company_id = str(uuid.uuid4())
    user = User(
        email="test@example.com",
        hashed_password="hash",
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    assert user.last_password_change is None


def test_user_set_password_reset_required(session):
    """Test setting password_reset_required flag."""
    company_id = str(uuid.uuid4())
    user = User(
        email="test@example.com",
        hashed_password="hash",
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    user.password_reset_required = True
    session.commit()
    session.refresh(user)

    assert user.password_reset_required is True


def test_user_update_last_password_change(session):
    """Test updating last_password_change timestamp."""
    from datetime import datetime, timezone

    company_id = str(uuid.uuid4())
    user = User(
        email="test@example.com",
        hashed_password="hash",
        first_name="Test",
        last_name="User",
        company_id=company_id,
    )
    session.add(user)
    session.commit()

    now = datetime.now(timezone.utc)
    user.last_password_change = now
    session.commit()
    session.refresh(user)

    assert user.last_password_change is not None
    # Compare timestamps (allowing small delta for test execution time)
    assert (
        abs(
            (
                user.last_password_change.replace(tzinfo=timezone.utc) - now
            ).total_seconds()
        )
        < 1
    )
