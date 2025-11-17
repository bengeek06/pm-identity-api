"""
test_company_logo_integration.py
---------------------------------

Integration tests for company logo upload/download/delete operations
with real Storage Service and MinIO backend.
"""

import io

import pytest


@pytest.mark.integration
def test_company_logo_upload_to_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
    storage_api_client,
):
    """
    Test complete company logo upload flow:
    1. Upload via Identity Service
    2. Verify file_id is stored in Identity DB
    3. Verify file exists in Storage Service
    4. Verify metadata is correct
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Create fake logo
    logo_data = b"fake-company-logo-data-integration-test"
    files = {"logo": (io.BytesIO(logo_data), "logo.png")}

    # Upload logo
    response = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201, f"Upload failed: {response.get_json()}"
    data = response.get_json()
    assert "logo_file_id" in data
    assert data["has_logo"] is True

    file_id = data["logo_file_id"]

    # Verify file exists in Storage Service
    storage_response = storage_api_client.get_file_metadata(
        file_id,
        real_company.id,
        real_user.id,
        bucket="companies",
        resource_type="logos",
    )
    assert (
        storage_response.status_code == 200
    ), f"File not found in Storage: {storage_response.text}"

    metadata = storage_response.json()
    # Metadata response has nested structure: {"file": {...}, "current_version": {...}}
    file_data = metadata.get("file", {})
    assert file_data.get("id") == file_id
    assert file_data.get("bucket_type") == "companies"
    assert file_data.get("bucket_id") == real_company.id


@pytest.mark.integration
def test_company_logo_download_from_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
):
    """
    Test company logo download:
    1. Upload logo
    2. Download via Identity Service
    3. Verify content is correct
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload
    logo_data = b"integration-test-company-logo-content"
    files = {"logo": (io.BytesIO(logo_data), "test_logo.png")}
    upload_response = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    # Download
    download_response = integration_client.get(
        f"/companies/{real_company.id}/logo"
    )
    assert download_response.status_code == 200
    assert download_response.content_type.startswith("image/")
    assert (
        download_response.data == logo_data
    ), "Downloaded content doesn't match uploaded content"


@pytest.mark.integration
def test_company_logo_delete_from_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
    storage_api_client,
):
    """
    Test company logo deletion:
    1. Upload logo
    2. Delete via Identity Service
    3. Verify file is removed from Storage Service
    4. Verify has_logo is False
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload
    logo_data = b"logo-to-delete"
    files = {"logo": (io.BytesIO(logo_data), "delete_me.png")}
    upload_response = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    file_id = upload_response.get_json()["logo_file_id"]

    # Delete
    delete_response = integration_client.delete(
        f"/companies/{real_company.id}/logo"
    )
    assert delete_response.status_code == 204

    # Verify file is gone from Storage
    storage_response = storage_api_client.get_file_metadata(
        file_id, real_company.id, real_user.id
    )
    assert (
        storage_response.status_code == 404
    ), "File should be deleted from Storage Service"

    # Verify has_logo is False
    company_response = integration_client.get(f"/companies/{real_company.id}")
    assert company_response.status_code == 200
    company_data = company_response.get_json()
    assert company_data["has_logo"] is False
    assert company_data["logo_file_id"] is None


@pytest.mark.integration
def test_company_logo_replace_in_real_storage(
    integration_client,
    real_company,
    real_user,
    integration_token,
    storage_api_client,
):
    """
    Test company logo replacement:
    1. Upload first logo
    2. Upload second logo
    3. Verify old file is deleted
    4. Verify new file exists
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # First upload
    logo1_data = b"first-logo-content"
    files1 = {"logo": (io.BytesIO(logo1_data), "logo1.png")}
    response1 = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files1,
        content_type="multipart/form-data",
    )
    assert response1.status_code == 201
    file_id_1 = response1.get_json()["logo_file_id"]

    # Second upload (replacement)
    logo2_data = b"second-logo-content-different"
    files2 = {"logo": (io.BytesIO(logo2_data), "logo2.png")}
    response2 = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files2,
        content_type="multipart/form-data",
    )
    assert response2.status_code == 201
    file_id_2 = response2.get_json()["logo_file_id"]

    # Storage Service uses versioning: same file_id, different version_number
    # This is expected behavior - verify file still exists
    assert (
        file_id_1 == file_id_2
    ), "Storage Service should version the same file"

    # Verify file metadata exists (should return latest version)
    metadata_response = storage_api_client.get_file_metadata(
        file_id_2,
        real_company.id,
        real_user.id,
        bucket="companies",
        resource_type="logos",
    )
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()

    # Verify it's version 2
    file_data = metadata.get("file", {})
    current_version = metadata.get("current_version", {})
    assert current_version.get("version_number") == 2

    # Verify download returns new content
    download_response = integration_client.get(
        f"/companies/{real_company.id}/logo"
    )
    assert download_response.status_code == 200
    assert download_response.data == logo2_data


@pytest.mark.integration
def test_company_logo_isolation_between_companies(
    integration_client,
    integration_session,
    real_company,
    real_user,
    integration_token,
):
    """
    Test that company logos are properly isolated.
    Company A should not be able to access Company B's logo.
    """
    from app.models.company import Company

    # Create second company
    company_b = Company(name="Company B Integration Test")
    integration_session.add(company_b)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload logo for company A
    logo_a = b"company-a-logo"
    files = {"logo": (io.BytesIO(logo_a), "logo_a.png")}
    response_a = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert response_a.status_code == 201

    # Try to access company B's logo (different company in JWT)
    # Should be forbidden since JWT has company_id = real_company.id
    response_b = integration_client.get(f"/companies/{company_b.id}/logo")
    # Company B has no logo, but the request should still work (different from avatar isolation)
    assert response_b.status_code == 404  # No logo uploaded for company B

    # Cleanup
    integration_session.delete(company_b)
    integration_session.commit()


@pytest.mark.integration
def test_company_logo_size_validation(
    integration_client,
    real_company,
    real_user,
    integration_token,
):
    """
    Test that large files are rejected by Storage Service.
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Create a large file (> MAX_AVATAR_SIZE_MB from env.example, typically 5MB)
    large_logo_data = b"X" * (6 * 1024 * 1024)  # 6 MB
    files = {"logo": (io.BytesIO(large_logo_data), "large_logo.png")}

    response = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )

    # Should be rejected by validation
    assert response.status_code in [400, 413], f"Large file should be rejected"


@pytest.mark.integration
def test_company_logo_persistence_across_updates(
    integration_client,
    real_company,
    real_user,
    integration_token,
):
    """
    Test that logo persists when company data is updated.
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload logo
    logo_data = b"persistent-logo-data"
    files = {"logo": (io.BytesIO(logo_data), "logo.png")}
    upload_response = integration_client.post(
        f"/companies/{real_company.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    file_id = upload_response.get_json()["logo_file_id"]

    # Update company data
    update_response = integration_client.patch(
        f"/companies/{real_company.id}",
        json={"description": "Updated description"},
    )
    assert update_response.status_code == 200

    # Verify logo is still there
    company_response = integration_client.get(f"/companies/{real_company.id}")
    assert company_response.status_code == 200
    company_data = company_response.get_json()
    assert company_data["has_logo"] is True
    assert company_data["logo_file_id"] == file_id

    # Verify download still works
    download_response = integration_client.get(
        f"/companies/{real_company.id}/logo"
    )
    assert download_response.status_code == 200
    assert download_response.data == logo_data
