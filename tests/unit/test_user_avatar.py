"""
Tests unitaires pour user_avatar.py

Ces tests valident la logique de gestion des avatars utilisateur,
sans appeler le Storage Service réel (mocks utilisés).
"""

import io
import uuid
from unittest import mock

import requests
from werkzeug.security import generate_password_hash

from app.models.user import User
from app.storage_helper import AvatarValidationError, StorageServiceError
from tests.unit.conftest import create_jwt_token, get_init_db_payload

# ============================================================================
# Tests: POST /users/<user_id>/avatar (upload)
# ============================================================================


def test_upload_avatar_user_not_found(client, app):
    """Test upload avatar pour utilisateur inexistant."""
    app.config["USE_STORAGE_SERVICE"] = True

    fake_user_id = str(uuid.uuid4())
    company_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, fake_user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock check_access
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.post(f"/users/{fake_user_id}/avatar")

        assert response.status_code == 404
        assert "not found" in response.get_json()["message"].lower()


def test_upload_avatar_access_denied_different_user(client, session):
    """Test que l'upload d'avatar d'un autre utilisateur est refusé."""
    # Create two users
    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user1_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Create second user
    user2 = User(
        email="user2@test.com",
        first_name="User",
        last_name="Two",
        company_id=company_id,
        hashed_password=generate_password_hash("password"),
    )
    session.add(user2)
    session.commit()
    user2_id = user2.id

    # User1 tries to upload avatar for User2
    jwt_token = create_jwt_token(company_id, user1_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.post(f"/users/{user2_id}/avatar")

        assert response.status_code == 403
        assert "access denied" in response.get_json()["message"].lower()


def test_upload_avatar_no_file_provided(client):
    """Test upload avatar sans fichier."""
    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.post(f"/users/{user_id}/avatar")

        assert response.status_code == 400
        assert "no avatar file" in response.get_json()["message"].lower()


def test_upload_avatar_storage_service_disabled(client, app):
    """Test upload avatar quand Storage Service désactivé."""
    app.config["USE_STORAGE_SERVICE"] = False

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        data = {"avatar": (io.BytesIO(b"fake image"), "avatar.jpg")}
        response = client.post(
            f"/users/{user_id}/avatar",
            data=data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 503
        assert "disabled" in response.get_json()["message"].lower()


@mock.patch("app.resources.user_avatar.upload_avatar_via_proxy")
def test_upload_avatar_success(mock_upload, client, app):
    """Test upload avatar avec succès."""
    app.config["USE_STORAGE_SERVICE"] = True

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Mock upload success
    mock_upload.return_value = {
        "file_id": "test-file-id-123",
        "object_key": "users/test/avatars/test.png",
    }

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        data = {"avatar": (io.BytesIO(b"fake image data"), "avatar.jpg")}
        response = client.post(
            f"/users/{user_id}/avatar",
            data=data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data["message"] == "Avatar uploaded successfully"
        assert json_data["avatar_file_id"] == "test-file-id-123"
        assert json_data["has_avatar"] is True

        # Verify user has avatar flag set
        user = User.get_by_id(user_id)
        assert user.has_avatar is True
        assert user.avatar_file_id == "test-file-id-123"


@mock.patch("app.resources.user_avatar.upload_avatar_via_proxy")
def test_upload_avatar_validation_error(mock_upload, client, app):
    """Test upload avatar avec fichier invalide."""
    app.config["USE_STORAGE_SERVICE"] = True

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Mock validation error
    mock_upload.side_effect = AvatarValidationError("File too large")

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        data = {"avatar": (io.BytesIO(b"x" * 10000000), "big.jpg")}
        response = client.post(
            f"/users/{user_id}/avatar",
            data=data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert "too large" in response.get_json()["message"].lower()


@mock.patch("app.resources.user_avatar.upload_avatar_via_proxy")
def test_upload_avatar_storage_service_error(mock_upload, client, app):
    """Test upload avatar avec erreur Storage Service."""
    app.config["USE_STORAGE_SERVICE"] = True

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Mock storage service error
    mock_upload.side_effect = StorageServiceError("Storage unavailable")

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        data = {"avatar": (io.BytesIO(b"fake image"), "avatar.jpg")}
        response = client.post(
            f"/users/{user_id}/avatar",
            data=data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 500
        assert "failed to upload" in response.get_json()["message"].lower()


# ============================================================================
# Tests: GET /users/<user_id>/avatar (retrieve)
# ============================================================================


def test_get_avatar_user_not_found(client):
    """Test récupération avatar pour utilisateur inexistant."""
    fake_user_id = str(uuid.uuid4())
    company_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, fake_user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.get(f"/users/{fake_user_id}/avatar")

        assert response.status_code == 404
        assert "not found" in response.get_json()["message"].lower()


def test_get_avatar_user_has_no_avatar(client):
    """Test récupération avatar pour utilisateur sans avatar."""
    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.get(f"/users/{user_id}/avatar")

        assert response.status_code == 404
        assert "no avatar" in response.get_json()["message"].lower()


def test_get_avatar_storage_service_disabled(client, app, session):
    """Test récupération avatar quand Storage Service désactivé."""
    app.config["USE_STORAGE_SERVICE"] = False

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Set avatar flag manually
    user = User.get_by_id(user_id)
    user.set_avatar("fake-file-id")
    session.commit()

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.get(f"/users/{user_id}/avatar")

        assert response.status_code == 503
        assert "disabled" in response.get_json()["message"].lower()


@mock.patch("app.resources.user_avatar.requests.get")
def test_get_avatar_success(mock_get, client, app, session):
    """Test récupération avatar avec succès."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Set avatar flag
    user = User.get_by_id(user_id)
    user.set_avatar("test-file-id")
    session.commit()

    # Mock Storage Service response
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "Content-Type": "image/jpeg",
        "Content-Disposition": "inline",
    }
    mock_response.iter_content = mock.Mock(
        return_value=[b"fake", b"image", b"data"]
    )
    mock_get.return_value = mock_response

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.get(f"/users/{user_id}/avatar")

        assert response.status_code == 200
        assert response.content_type == "image/jpeg"
        assert b"fakeimagedata" in response.data


@mock.patch("app.resources.user_avatar.requests.get")
def test_get_avatar_storage_service_error(mock_get, client, app, session):
    """Test récupération avatar avec erreur Storage Service."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Set avatar flag
    user = User.get_by_id(user_id)
    user.set_avatar("test-file-id")
    session.commit()

    # Mock Storage Service error
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_get.return_value = mock_response

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.get(f"/users/{user_id}/avatar")

        assert response.status_code == 500


@mock.patch("app.resources.user_avatar.requests.get")
def test_get_avatar_timeout(mock_get, client, app, session):
    """Test récupération avatar avec timeout."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Set avatar flag
    user = User.get_by_id(user_id)
    user.set_avatar("test-file-id")
    session.commit()

    # Mock timeout
    mock_get.side_effect = requests.exceptions.Timeout("Timeout")

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.get(f"/users/{user_id}/avatar")

        assert response.status_code == 504
        assert "timeout" in response.get_json()["message"].lower()


# ============================================================================
# Tests: DELETE /users/<user_id>/avatar
# ============================================================================


def test_delete_avatar_user_not_found(client):
    """Test suppression avatar pour utilisateur inexistant."""
    fake_user_id = str(uuid.uuid4())
    company_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, fake_user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.delete(f"/users/{fake_user_id}/avatar")

        assert response.status_code == 404
        assert "not found" in response.get_json()["message"].lower()


def test_delete_avatar_access_denied_different_user(client, session):
    """Test que la suppression d'avatar d'un autre utilisateur est refusée."""
    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user1_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Create second user
    user2 = User(
        email="user2@test.com",
        first_name="User",
        last_name="Two",
        company_id=company_id,
        hashed_password=generate_password_hash("password"),
    )
    user2.set_avatar("fake-file-id")
    session.add(user2)
    session.commit()
    user2_id = user2.id

    # User1 tries to delete avatar for User2
    jwt_token = create_jwt_token(company_id, user1_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.delete(f"/users/{user2_id}/avatar")

        assert response.status_code == 403
        assert "access denied" in response.get_json()["message"].lower()


def test_delete_avatar_user_has_no_avatar(client):
    """Test suppression avatar pour utilisateur sans avatar."""
    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.delete(f"/users/{user_id}/avatar")

        assert response.status_code == 404
        assert "no avatar" in response.get_json()["message"].lower()


def test_delete_avatar_storage_service_disabled(client, app, session):
    """Test suppression avatar quand Storage Service désactivé."""
    app.config["USE_STORAGE_SERVICE"] = False

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Set avatar flag
    user = User.get_by_id(user_id)
    user.set_avatar("fake-file-id")
    session.commit()

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.delete(f"/users/{user_id}/avatar")

        assert response.status_code == 204

        # Verify flag cleared in database
        user = User.get_by_id(user_id)
        assert user.has_avatar is False


@mock.patch("app.resources.user_avatar.delete_avatar")
def test_delete_avatar_success(mock_delete, client, app, session):
    """Test suppression avatar avec succès."""
    app.config["USE_STORAGE_SERVICE"] = True

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Set avatar flag
    user = User.get_by_id(user_id)
    user.set_avatar("test-file-id")
    session.commit()

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.delete(f"/users/{user_id}/avatar")

        assert response.status_code == 204

        # Verify delete was called
        mock_delete.assert_called_once_with(
            user_id, company_id, "test-file-id"
        )

        # Verify flag cleared in database
        user = User.get_by_id(user_id)
        assert user.has_avatar is False
        assert user.avatar_file_id is None


@mock.patch("app.resources.user_avatar.delete_avatar")
def test_delete_avatar_continues_on_storage_error(
    mock_delete, client, app, session
):
    """Test que la suppression continue même si Storage Service échoue."""
    app.config["USE_STORAGE_SERVICE"] = True

    init_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_payload)
    assert resp.status_code == 201

    user_id = resp.get_json()["user"]["id"]
    company_id = resp.get_json()["company"]["id"]

    # Set avatar flag
    user = User.get_by_id(user_id)
    user.set_avatar("test-file-id")
    session.commit()

    # Mock storage error
    mock_delete.side_effect = Exception("Storage error")

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {"access_granted": True}

    with mock.patch("requests.post", return_value=mock_check_access):
        response = client.delete(f"/users/{user_id}/avatar")

        # Should still succeed (database cleanup)
        assert response.status_code == 204

        # Verify flag still cleared despite storage error
        user = User.get_by_id(user_id)
        assert user.has_avatar is False
        assert user.avatar_file_id is None
