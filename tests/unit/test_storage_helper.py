# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Tests unitaires pour storage_helper.py

Ces tests valident la logique métier de l'interaction avec Storage Service,
sans réellement appeler le service (mocks utilisés).
"""

import uuid
from unittest import mock

import pytest

from app.storage_helper import (AvatarValidationError,
                                StorageServiceError, delete_avatar,
                                delete_logo, is_storage_service_enabled,
                                upload_avatar_via_proxy, upload_logo_via_proxy,
                                validate_avatar)

# ============================================================================
# Tests: is_storage_service_enabled
# ============================================================================


def test_is_storage_service_enabled_returns_true(app):
    """Test que is_storage_service_enabled retourne True quand activé."""
    app.config["USE_STORAGE_SERVICE"] = True

    with app.app_context():
        assert is_storage_service_enabled() is True


def test_is_storage_service_enabled_returns_false(app):
    """Test que is_storage_service_enabled retourne False quand désactivé."""
    app.config["USE_STORAGE_SERVICE"] = False

    with app.app_context():
        assert is_storage_service_enabled() is False


def test_is_storage_service_enabled_default_false(app):
    """Test que is_storage_service_enabled est False par défaut."""
    app.config.pop("USE_STORAGE_SERVICE", None)

    with app.app_context():
        assert is_storage_service_enabled() is False


# ============================================================================
# Tests: validate_avatar
# ============================================================================


def test_validate_avatar_with_valid_jpeg_succeeds(app):
    """Test que validate_avatar accepte un JPEG valide."""
    with app.app_context():
        file_data = b"fake-jpeg-data" * 100
        validate_avatar(file_data, "image/jpeg")
        # No exception = success


def test_validate_avatar_with_valid_png_succeeds(app):
    """Test que validate_avatar accepte un PNG valide."""
    with app.app_context():
        file_data = b"fake-png-data" * 100
        validate_avatar(file_data, "image/png")


def test_validate_avatar_with_valid_webp_succeeds(app):
    """Test que validate_avatar accepte un WebP valide."""
    with app.app_context():
        file_data = b"fake-webp-data" * 100
        validate_avatar(file_data, "image/webp")


def test_validate_avatar_with_empty_file_raises_error(app):
    """Test que validate_avatar rejette un fichier vide."""
    with app.app_context():
        with pytest.raises(AvatarValidationError, match="empty"):
            validate_avatar(b"", "image/jpeg")


def test_validate_avatar_with_too_large_file_raises_error(app):
    """Test que validate_avatar rejette un fichier trop gros."""
    app.config["MAX_AVATAR_SIZE_MB"] = 1  # 1 MB max

    with app.app_context():
        # Create 2 MB file
        file_data = b"x" * (2 * 1024 * 1024)

        with pytest.raises(AvatarValidationError, match="too large"):
            validate_avatar(file_data, "image/jpeg")


def test_validate_avatar_with_invalid_content_type_raises_error(app):
    """Test que validate_avatar rejette un type de fichier invalide."""
    with app.app_context():
        file_data = b"fake-pdf-data" * 100

        with pytest.raises(
            AvatarValidationError, match="Invalid content type"
        ):
            validate_avatar(file_data, "application/pdf")


def test_validate_avatar_respects_custom_max_size(app):
    """Test que validate_avatar respecte la taille max personnalisée."""
    with app.app_context():
        file_data = b"x" * 1000

        # Should pass with large max_size
        validate_avatar(file_data, "image/jpeg", max_size=10000)

        # Should fail with small max_size
        with pytest.raises(AvatarValidationError, match="too large"):
            validate_avatar(file_data, "image/jpeg", max_size=500)


# ============================================================================
# Tests: upload_avatar_via_proxy
# ============================================================================


def test_upload_avatar_when_storage_disabled_returns_mock(app):
    """Test que upload_avatar retourne des données mock quand Storage désactivé."""
    app.config["USE_STORAGE_SERVICE"] = False

    with app.app_context():
        user_id = str(uuid.uuid4())
        company_id = str(uuid.uuid4())
        file_data = b"fake-image-data"

        result = upload_avatar_via_proxy(
            user_id, company_id, file_data, "image/jpeg", "avatar.jpg"
        )

        assert "file_id" in result
        assert "mock-file-id" in result["file_id"]
        assert user_id in result["file_id"]


def test_upload_avatar_with_invalid_file_raises_validation_error(app):
    """Test que upload_avatar valide le fichier avant upload."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    with app.app_context():
        user_id = str(uuid.uuid4())
        company_id = str(uuid.uuid4())

        # Empty file should fail validation
        with pytest.raises(AvatarValidationError, match="empty"):
            upload_avatar_via_proxy(
                user_id, company_id, b"", "image/jpeg", "avatar.jpg"
            )


@mock.patch("app.storage_helper.requests.post")
def test_upload_avatar_with_valid_file_succeeds(mock_post, app):
    """Test que upload_avatar réussit avec un fichier valide."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    # Mock successful Storage Service response
    mock_response = mock.Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "file_id": "test-file-id-123",
        "object_key": "users/test-user/avatars/test.png",
    }
    mock_post.return_value = mock_response

    with app.app_context():
        user_id = str(uuid.uuid4())
        company_id = str(uuid.uuid4())
        file_data = b"fake-image-data" * 100

        result = upload_avatar_via_proxy(
            user_id, company_id, file_data, "image/jpeg", "avatar.jpg"
        )

        assert result["file_id"] == "test-file-id-123"
        assert "object_key" in result

        # Verify requests.post was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://storage:5001/upload/proxy"
        assert call_args[1]["headers"]["X-User-ID"] == user_id
        assert call_args[1]["headers"]["X-Company-ID"] == company_id


@mock.patch("app.storage_helper.requests.post")
def test_upload_avatar_handles_storage_service_error(mock_post, app):
    """Test que upload_avatar gère les erreurs du Storage Service."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    # Mock Storage Service error
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = Exception("Storage error")
    mock_post.return_value = mock_response

    with app.app_context():
        user_id = str(uuid.uuid4())
        company_id = str(uuid.uuid4())
        file_data = b"fake-image-data" * 100

        with pytest.raises(Exception, match="Storage error"):
            upload_avatar_via_proxy(
                user_id, company_id, file_data, "image/jpeg", "avatar.jpg"
            )


@mock.patch("app.storage_helper.requests.post")
def test_upload_avatar_handles_missing_file_id(mock_post, app):
    """Test que upload_avatar gère une réponse sans file_id."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    # Mock response without file_id
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}  # Missing file_id
    mock_post.return_value = mock_response

    with app.app_context():
        user_id = str(uuid.uuid4())
        company_id = str(uuid.uuid4())
        file_data = b"fake-image-data" * 100

        with pytest.raises(
            StorageServiceError, match="did not return file_id"
        ):
            upload_avatar_via_proxy(
                user_id, company_id, file_data, "image/jpeg", "avatar.jpg"
            )


# ============================================================================
# Tests: upload_logo_via_proxy
# ============================================================================


@mock.patch("app.storage_helper.requests.post")
def test_upload_logo_with_valid_file_succeeds(mock_post, app):
    """Test que upload_logo réussit avec un fichier valide."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    mock_response = mock.Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "file_id": "logo-file-id-456",
        "object_key": "companies/test-company/logos/test.png",
    }
    mock_post.return_value = mock_response

    with app.app_context():
        company_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        file_data = b"fake-logo-data" * 100

        result = upload_logo_via_proxy(
            company_id, user_id, file_data, "image/png", "logo.png"
        )

        assert result["file_id"] == "logo-file-id-456"
        assert "object_key" in result

        # Verify correct headers
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["X-Company-ID"] == company_id
        assert call_args[1]["headers"]["X-User-ID"] == user_id


# ============================================================================
# Tests: delete_avatar
# ============================================================================


def test_delete_avatar_when_storage_disabled_succeeds(app):
    """Test que delete_avatar réussit quand Storage désactivé."""
    app.config["USE_STORAGE_SERVICE"] = False

    with app.app_context():
        # Should not raise exception
        delete_avatar("user-id", "company-id", "file-id")


@mock.patch("app.storage_helper.requests.delete")
def test_delete_avatar_succeeds(mock_delete, app):
    """Test que delete_avatar supprime un fichier."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    mock_response = mock.Mock()
    mock_response.status_code = 204  # No content
    mock_delete.return_value = mock_response

    with app.app_context():
        user_id = str(uuid.uuid4())
        company_id = str(uuid.uuid4())
        file_id = "file-to-delete"

        # Should not raise exception
        delete_avatar(user_id, company_id, file_id)

        # Verify DELETE called
        mock_delete.assert_called_once()
        call_args = mock_delete.call_args
        assert call_args[0][0] == "http://storage:5001/delete"
        assert call_args[1]["json"]["file_id"] == file_id
        assert call_args[1]["headers"]["X-User-ID"] == user_id


@mock.patch("app.storage_helper.requests.delete")
def test_delete_avatar_handles_not_found(mock_delete, app):
    """Test que delete_avatar gère fichier déjà supprimé (404 est accepté)."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    mock_response = mock.Mock()
    mock_response.status_code = 404
    mock_delete.return_value = mock_response

    with app.app_context():
        # Should NOT raise exception for 404 (already deleted)
        delete_avatar("user-id", "company-id", "missing-file")

        # Verify it was called
        mock_delete.assert_called_once()


# ============================================================================
# Tests: delete_logo
# ============================================================================


@mock.patch("app.storage_helper.requests.delete")
def test_delete_logo_succeeds(mock_delete, app):
    """Test que delete_logo supprime un logo."""
    app.config["USE_STORAGE_SERVICE"] = True
    app.config["STORAGE_SERVICE_URL"] = "http://storage:5001"

    mock_response = mock.Mock()
    mock_response.status_code = 204
    mock_delete.return_value = mock_response

    with app.app_context():
        company_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Should not raise exception
        delete_logo(company_id, user_id, "logo-file-id")

        # Verify DELETE called
        mock_delete.assert_called_once()
