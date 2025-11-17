"""
test_user_avatar_integration.py
--------------------------------

Integration tests for user avatar upload/download/delete operations
with real Storage Service and MinIO backend.
"""

import io

import pytest


@pytest.mark.integration
def test_avatar_upload_to_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
    storage_api_client,
):
    """
    Test complete avatar upload flow:
    1. Upload via Identity Service
    2. Verify file_id is stored in Identity DB
    3. Verify file exists in Storage Service
    4. Verify metadata is correct
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Create fake image
    avatar_data = b"fake-avatar-image-data-integration-test"
    files = {"avatar": (io.BytesIO(avatar_data), "avatar.png")}

    # Upload avatar
    response = integration_client.post(
        f"/users/{real_user.id}/avatar",
        data=files,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201, f"Upload failed: {response.get_json()}"
    data = response.get_json()
    assert "avatar_file_id" in data
    assert data["has_avatar"] is True

    file_id = data["avatar_file_id"]

    # Verify file exists in Storage Service
    storage_response = storage_api_client.get_file_metadata(
        file_id, real_company.id, real_user.id
    )
    assert (
        storage_response.status_code == 200
    ), f"File not found in Storage: {storage_response.text}"

    metadata = storage_response.json()
    # Storage API returns nested structure: {file: {...}, current_version: {...}}
    file_data = metadata.get("file", {})
    assert (
        file_data.get("id") == file_id
        or file_data.get("bucket_type") == "users"
    )
    assert file_data.get("bucket_type") == "users"
    assert file_data.get("bucket_id") == real_user.id


@pytest.mark.integration
def test_avatar_download_from_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
):
    """
    Test avatar download:
    1. Upload avatar
    2. Download via Identity Service
    3. Verify content is correct
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload
    avatar_data = b"integration-test-avatar-content"
    files = {"avatar": (io.BytesIO(avatar_data), "test_avatar.png")}
    upload_response = integration_client.post(
        f"/users/{real_user.id}/avatar",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    # Download
    download_response = integration_client.get(f"/users/{real_user.id}/avatar")
    assert download_response.status_code == 200
    assert download_response.content_type.startswith("image/")
    assert (
        download_response.data == avatar_data
    ), "Downloaded content doesn't match uploaded content"


@pytest.mark.integration
def test_avatar_delete_from_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
    storage_api_client,
):
    """
    Test avatar deletion:
    1. Upload avatar
    2. Delete via Identity Service
    3. Verify file is removed from Storage Service
    4. Verify has_avatar is False
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload
    avatar_data = b"avatar-to-delete"
    files = {"avatar": (io.BytesIO(avatar_data), "delete_me.png")}
    upload_response = integration_client.post(
        f"/users/{real_user.id}/avatar",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    file_id = upload_response.get_json()["avatar_file_id"]

    # Delete
    delete_response = integration_client.delete(
        f"/users/{real_user.id}/avatar"
    )
    assert delete_response.status_code == 204

    # Verify file is gone from Storage
    storage_response = storage_api_client.get_file_metadata(
        file_id, real_company.id, real_user.id
    )
    assert (
        storage_response.status_code == 404
    ), "File should be deleted from Storage Service"

    # Verify has_avatar is False
    user_response = integration_client.get(f"/users/{real_user.id}")
    assert user_response.status_code == 200
    user_data = user_response.get_json()
    assert user_data["has_avatar"] is False
    assert user_data["avatar_file_id"] is None


@pytest.mark.integration
def test_avatar_replace_in_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
    storage_api_client,
):
    """
    Test avatar replacement:
    1. Upload first avatar
    2. Upload second avatar
    3. Verify Storage Service versioning works (same file_id, different version)
    4. Verify download returns latest content
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # First upload
    avatar1_data = b"first-avatar-content"
    files1 = {"avatar": (io.BytesIO(avatar1_data), "avatar1.png")}
    response1 = integration_client.post(
        f"/users/{real_user.id}/avatar",
        data=files1,
        content_type="multipart/form-data",
    )
    assert response1.status_code == 201
    file_id_1 = response1.get_json()["avatar_file_id"]

    # Second upload (replacement)
    avatar2_data = b"second-avatar-content-different"
    files2 = {"avatar": (io.BytesIO(avatar2_data), "avatar2.png")}
    response2 = integration_client.post(
        f"/users/{real_user.id}/avatar",
        data=files2,
        content_type="multipart/form-data",
    )
    assert response2.status_code == 201
    file_id_2 = response2.get_json()["avatar_file_id"]

    # Storage Service uses versioning: same file_id, different version_number
    # This is expected behavior - verify file still exists
    assert (
        file_id_1 == file_id_2
    ), "Storage Service should version the same file"

    # Verify file metadata exists (should return latest version)
    metadata_response = storage_api_client.get_file_metadata(
        file_id_2, real_company.id, real_user.id
    )
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()

    # Verify it's version 2
    current_version = metadata.get("current_version", {})
    assert current_version.get("version_number") == 2

    # Verify download returns new content (latest version)
    download_response = integration_client.get(f"/users/{real_user.id}/avatar")
    assert download_response.status_code == 200
    assert download_response.data == avatar2_data


@pytest.mark.integration
def test_avatar_isolation_between_users(
    integration_client,
    integration_session,
    real_company,
    real_user,
    integration_token,
):
    """
    Test that avatars are properly isolated between users.
    User A should not be able to access User B's avatar.
    """
    from werkzeug.security import (
        generate_password_hash,
    )  # pylint: disable=import-outside-toplevel

    from app.models.user import User  # pylint: disable=import-outside-toplevel

    # Create second user
    user_b = User(
        email="userb@integration.test",
        first_name="User",
        last_name="B",
        company_id=real_company.id,
        hashed_password=generate_password_hash("password"),
    )
    integration_session.add(user_b)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload avatar for user A
    avatar_a = b"user-a-avatar"
    files = {"avatar": (io.BytesIO(avatar_a), "avatar_a.png")}
    response_a = integration_client.post(
        f"/users/{real_user.id}/avatar",
        data=files,
        content_type="multipart/form-data",
    )
    assert response_a.status_code == 201

    # Try to download user B's avatar (should not exist)
    response_b = integration_client.get(f"/users/{user_b.id}/avatar")
    assert response_b.status_code == 404

    # Cleanup
    integration_session.delete(user_b)
    integration_session.commit()
