"""
test_company_logo.py
--------------------

Test suite for company logo upload/download/delete operations.
Tests the /companies/{company_id}/logo endpoints.
"""

import io
import uuid

from app.models.company import Company
from tests.conftest import create_jwt_token


def test_post_company_logo_service_disabled(client, session):
    """
    Test POST /companies/{id}/logo when Storage Service is disabled.
    Should return 503 Service Unavailable.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    company = Company(id=company_id, name="TestCompany")
    session.add(company)
    session.commit()

    # Create a fake image file
    logo_data = b"fake-image-data"
    data = {"logo": (io.BytesIO(logo_data), "logo.png")}

    response = client.post(
        f"/companies/{company_id}/logo",
        data=data,
        content_type="multipart/form-data",
    )

    # Should return 503 since USE_STORAGE_SERVICE=false in tests
    assert response.status_code == 503
    data = response.get_json()
    assert "Storage Service disabled" in data["message"]


def test_post_company_logo_no_file(client, session):
    """
    Test POST /companies/{id}/logo without providing a file.
    Should return 400 Bad Request.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    company = Company(id=company_id, name="TestCompany")
    session.add(company)
    session.commit()

    response = client.post(
        f"/companies/{company_id}/logo",
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "No logo file provided" in data["message"]


def test_post_company_logo_company_not_found(client, session):
    """
    Test POST /companies/{id}/logo for non-existent company.
    Should return 404 Not Found.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    logo_data = b"fake-image-data"
    data = {"logo": (io.BytesIO(logo_data), "logo.png")}

    response = client.post(
        f"/companies/{company_id}/logo",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 404
    data = response.get_json()
    assert "Company not found" in data["message"]


def test_post_company_logo_wrong_company_id(client, session):
    """
    Test POST /companies/{id}/logo with mismatched company_id in JWT.
    Should return 403 Forbidden.
    """
    company_id = str(uuid.uuid4())
    other_company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    # Create company with different ID
    company = Company(id=other_company_id, name="TestCompany")
    session.add(company)
    session.commit()

    logo_data = b"fake-image-data"
    data = {"logo": (io.BytesIO(logo_data), "logo.png")}

    response = client.post(
        f"/companies/{other_company_id}/logo",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 403
    data = response.get_json()
    assert "cannot manage other company" in data["message"]


def test_get_company_logo_no_logo(client, session):
    """
    Test GET /companies/{id}/logo when company has no logo.
    Should return 404 Not Found.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    company = Company(id=company_id, name="TestCompany")
    session.add(company)
    session.commit()

    response = client.get(f"/companies/{company_id}/logo")

    assert response.status_code == 404
    data = response.get_json()
    assert "has no logo" in data["message"]


def test_get_company_logo_service_disabled(client, session):
    """
    Test GET /companies/{id}/logo when Storage Service is disabled.
    Should return 404.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    company = Company(id=company_id, name="TestCompany")
    company.set_logo("file-id-123")
    session.add(company)
    session.commit()

    response = client.get(f"/companies/{company_id}/logo")

    # Should return 404 since USE_STORAGE_SERVICE=false in tests
    assert response.status_code == 404
    data = response.get_json()
    assert "Storage Service disabled" in data["message"]


def test_delete_company_logo_success(client, session):
    """
    Test DELETE /companies/{id}/logo successfully removes logo reference.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    company = Company(id=company_id, name="TestCompany")
    company.set_logo("file-id-123")
    session.add(company)
    session.commit()

    assert company.has_logo is True

    response = client.delete(f"/companies/{company_id}/logo")

    assert response.status_code == 204

    # Verify logo was removed from database
    session.refresh(company)
    assert company.logo_file_id is None
    assert company.has_logo is False


def test_delete_company_logo_no_logo(client, session):
    """
    Test DELETE /companies/{id}/logo when company has no logo.
    Should return 404.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    company = Company(id=company_id, name="TestCompany")
    session.add(company)
    session.commit()

    response = client.delete(f"/companies/{company_id}/logo")

    assert response.status_code == 404
    data = response.get_json()
    assert "has no logo to delete" in data["message"]


def test_delete_company_logo_company_not_found(client, session):
    """
    Test DELETE /companies/{id}/logo for non-existent company.
    Should return 404.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.delete(f"/companies/{company_id}/logo")

    assert response.status_code == 404
    data = response.get_json()
    assert "Company not found" in data["message"]


def test_delete_company_logo_wrong_company_id(client, session):
    """
    Test DELETE /companies/{id}/logo with mismatched company_id in JWT.
    Should return 403 Forbidden.
    """
    company_id = str(uuid.uuid4())
    other_company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    # Create company with different ID
    company = Company(id=other_company_id, name="TestCompany")
    company.set_logo("file-id-123")
    session.add(company)
    session.commit()

    response = client.delete(f"/companies/{other_company_id}/logo")

    assert response.status_code == 403
    data = response.get_json()
    assert "cannot delete other company" in data["message"]
