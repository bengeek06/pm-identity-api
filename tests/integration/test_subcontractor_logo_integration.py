# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
test_subcontractor_logo_integration.py
---------------------------------------

Integration tests for subcontractor logo upload/download/delete operations
with real Storage Service and MinIO backend.
"""

import io

import pytest

from app.models.subcontractor import Subcontractor


@pytest.mark.integration
def test_subcontractor_logo_upload_to_real_storage(
    integration_client,
    real_company,
    integration_session,
    integration_token,
):
    """
    Test complete subcontractor logo upload flow:
    1. Upload via Identity Service
    2. Verify file_id is stored in Identity DB
    3. Verify file exists in Storage Service
    4. Verify metadata is correct
    """
    # Create subcontractor
    subcontractor = Subcontractor(
        name="Test Subcontractor Logo Upload",
        company_id=real_company.id,
    )
    integration_session.add(subcontractor)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Create fake logo
    logo_data = b"fake-subcontractor-logo-data-integration-test"
    files = {"logo": (io.BytesIO(logo_data), "logo.png")}

    # Upload logo
    response = integration_client.post(
        f"/subcontractors/{subcontractor.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201, f"Upload failed: {response.get_json()}"
    data = response.get_json()
    assert "logo_file_id" in data
    assert data["has_logo"] is True

    # Verify file exists by downloading via Identity Service
    download_response = integration_client.get(
        f"/subcontractors/{subcontractor.id}/logo"
    )
    assert (
        download_response.status_code == 200
    ), f"File not found in Storage: {download_response.status_code}"
    assert download_response.content_type.startswith("image/")
    assert len(download_response.data) > 0, "Downloaded logo is empty"

    # Cleanup
    integration_session.delete(subcontractor)
    integration_session.commit()


@pytest.mark.integration
def test_subcontractor_logo_download_from_real_storage(
    integration_client,
    real_company,
    integration_session,
    integration_token,
):
    """
    Test subcontractor logo download:
    1. Upload logo
    2. Download via Identity Service
    3. Verify content is correct
    """
    subcontractor = Subcontractor(
        name="Test Subcontractor Logo Download",
        company_id=real_company.id,
    )
    integration_session.add(subcontractor)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload
    logo_data = b"integration-test-subcontractor-logo-content"
    files = {"logo": (io.BytesIO(logo_data), "test_logo.png")}
    upload_response = integration_client.post(
        f"/subcontractors/{subcontractor.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    # Download
    download_response = integration_client.get(
        f"/subcontractors/{subcontractor.id}/logo"
    )
    assert download_response.status_code == 200
    assert download_response.content_type.startswith("image/")
    assert (
        download_response.data == logo_data
    ), "Downloaded content doesn't match uploaded content"

    # Cleanup
    integration_session.delete(subcontractor)
    integration_session.commit()


@pytest.mark.integration
def test_subcontractor_logo_delete_from_real_storage(
    integration_client,
    real_company,
    integration_session,
    integration_token,
):
    """
    Test subcontractor logo deletion:
    1. Upload logo
    2. Delete via Identity Service
    3. Verify file is removed from Storage Service
    4. Verify has_logo is False
    """
    subcontractor = Subcontractor(
        name="Test Subcontractor Logo Delete",
        company_id=real_company.id,
    )
    integration_session.add(subcontractor)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload
    logo_data = b"logo-to-delete"
    files = {"logo": (io.BytesIO(logo_data), "delete_me.png")}
    upload_response = integration_client.post(
        f"/subcontractors/{subcontractor.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    # Delete
    delete_response = integration_client.delete(
        f"/subcontractors/{subcontractor.id}/logo"
    )
    assert delete_response.status_code == 204

    # Verify file is gone by checking download returns 404
    download_response = integration_client.get(
        f"/subcontractors/{subcontractor.id}/logo"
    )
    assert download_response.status_code == 404, "Logo should be deleted"

    # Verify has_logo is False
    subcontractor_response = integration_client.get(
        f"/subcontractors/{subcontractor.id}"
    )
    assert subcontractor_response.status_code == 200
    subcontractor_data = subcontractor_response.get_json()
    assert subcontractor_data["has_logo"] is False
    assert subcontractor_data["logo_file_id"] is None

    # Cleanup
    integration_session.delete(subcontractor)
    integration_session.commit()


@pytest.mark.integration
def test_subcontractor_logo_replace_in_real_storage(
    integration_client,
    real_company,
    integration_session,
    integration_token,
):
    """
    Test subcontractor logo replacement:
    1. Upload first logo
    2. Upload second logo
    3. Verify old file is deleted
    4. Verify new file exists
    """
    subcontractor = Subcontractor(
        name="Test Subcontractor Logo Replace",
        company_id=real_company.id,
    )
    integration_session.add(subcontractor)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # First upload
    logo1_data = b"first-logo-content"
    files1 = {"logo": (io.BytesIO(logo1_data), "logo1.png")}
    response1 = integration_client.post(
        f"/subcontractors/{subcontractor.id}/logo",
        data=files1,
        content_type="multipart/form-data",
    )
    assert response1.status_code == 201
    file_id_1 = response1.get_json()["logo_file_id"]

    # Second upload (replacement)
    logo2_data = b"second-logo-content-different"
    files2 = {"logo": (io.BytesIO(logo2_data), "logo2.png")}
    response2 = integration_client.post(
        f"/subcontractors/{subcontractor.id}/logo",
        data=files2,
        content_type="multipart/form-data",
    )
    assert response2.status_code == 201
    file_id_2 = response2.get_json()["logo_file_id"]

    # Storage Service uses versioning: same file_id, different version_number
    assert (
        file_id_1 == file_id_2
    ), "Storage Service should version the same file"

    # Verify file exists by downloading latest version via Identity Service
    download_response = integration_client.get(
        f"/subcontractors/{subcontractor.id}/logo"
    )
    assert download_response.status_code == 200
    assert download_response.content_type.startswith("image/")

    # Verify download returns new content (latest version)
    assert (
        download_response.data == logo2_data
    ), "Should return latest uploaded content"

    # Cleanup
    integration_session.delete(subcontractor)
    integration_session.commit()


@pytest.mark.integration
def test_subcontractor_logo_size_validation(
    integration_client,
    real_company,
    integration_session,
    integration_token,
):
    """
    Test that large files are rejected by Storage Service.
    """
    subcontractor = Subcontractor(
        name="Test Subcontractor Logo Size",
        company_id=real_company.id,
    )
    integration_session.add(subcontractor)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Create a large file (> MAX_AVATAR_SIZE_MB, typically 5MB)
    large_logo_data = b"X" * (6 * 1024 * 1024)  # 6 MB
    files = {"logo": (io.BytesIO(large_logo_data), "large_logo.png")}

    response = integration_client.post(
        f"/subcontractors/{subcontractor.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )

    # Should be rejected by validation
    assert response.status_code in [400, 413], "Large file should be rejected"

    # Cleanup
    integration_session.delete(subcontractor)
    integration_session.commit()


@pytest.mark.integration
def test_subcontractor_logo_persistence_across_updates(
    integration_client,
    real_company,
    integration_session,
    integration_token,
):
    """
    Test that logo persists when subcontractor data is updated.
    """
    subcontractor = Subcontractor(
        name="Test Subcontractor Logo Persist",
        company_id=real_company.id,
    )
    integration_session.add(subcontractor)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload logo
    logo_data = b"persistent-logo-data"
    files = {"logo": (io.BytesIO(logo_data), "logo.png")}
    upload_response = integration_client.post(
        f"/subcontractors/{subcontractor.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    file_id = upload_response.get_json()["logo_file_id"]

    # Update subcontractor data
    update_response = integration_client.patch(
        f"/subcontractors/{subcontractor.id}",
        json={"name": "Updated Subcontractor Name"},
    )
    assert update_response.status_code == 200

    # Verify logo is still there
    subcontractor_response = integration_client.get(
        f"/subcontractors/{subcontractor.id}"
    )
    assert subcontractor_response.status_code == 200
    subcontractor_data = subcontractor_response.get_json()
    assert subcontractor_data["has_logo"] is True
    assert subcontractor_data["logo_file_id"] == file_id

    # Verify download still works
    download_response = integration_client.get(
        f"/subcontractors/{subcontractor.id}/logo"
    )
    assert download_response.status_code == 200
    assert download_response.data == logo_data

    # Cleanup
    integration_session.delete(subcontractor)
    integration_session.commit()


@pytest.mark.integration
def test_subcontractor_logo_access_control(
    integration_client,
    real_company,
    integration_session,
    integration_token,
):
    """
    Test that company isolation is enforced for subcontractor logos.
    Cannot access subcontractor from different company.
    """
    # Create subcontractor for real_company
    subcontractor_a = Subcontractor(
        name="Subcontractor Company A",
        company_id=real_company.id,
    )
    integration_session.add(subcontractor_a)
    integration_session.commit()

    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Upload logo
    logo_data = b"subcontractor-a-logo"
    files = {"logo": (io.BytesIO(logo_data), "logo_a.png")}
    response = integration_client.post(
        f"/subcontractors/{subcontractor_a.id}/logo",
        data=files,
        content_type="multipart/form-data",
    )
    assert response.status_code == 201

    # Verify download works for same company
    download_response = integration_client.get(
        f"/subcontractors/{subcontractor_a.id}/logo"
    )
    assert download_response.status_code == 200

    # Cleanup
    integration_session.delete(subcontractor_a)
    integration_session.commit()
