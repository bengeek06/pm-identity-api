# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Test cases for the Customer resource in the PM Identity API.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.customer import Customer
from tests.unit.conftest import create_jwt_token


@pytest.fixture
def authenticated_client(client):
    """
    Fixture that provides an authenticated client with JWT cookie.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")
    return client


@pytest.fixture
def test_customer_for_update(session):
    """
    Fixture that creates a customer for update/delete tests.
    """
    customer = Customer(name="ToBeUpdated", company_id=str(uuid.uuid4()))
    session.add(customer)
    session.commit()
    return customer


def setup_monkeypatch_integrity_error(monkeypatch):
    """
    Helper function to setup monkeypatch for IntegrityError simulation.
    """

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)


def setup_monkeypatch_sqlalchemy_error(monkeypatch):
    """
    Helper function to setup monkeypatch for SQLAlchemyError simulation.
    """

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)


@pytest.fixture
def authenticated_client_with_company(client):
    """
    Fixture that provides an authenticated client and returns both client and company_id.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")
    client.company_id = company_id  # Store for test access
    return client


##################################################
# Test cases for GET /customers
##################################################
def test_get_all_customers(authenticated_client):
    """
    Test retrieving all customers.
    """
    response = authenticated_client.get("/customers")
    assert response.status_code == 200
    assert response.is_json
    result = response.get_json()
    assert "data" in result
    assert "pagination" in result
    data = result["data"]
    assert isinstance(data, list)
    assert len(data) == 0
    assert result["pagination"]["total"] == 0


def test_get_customers_single(authenticated_client, session):
    """
    Test retrieving a single customer by ID.
    """
    customer = Customer(name="Test Customer", company_id=str(uuid.uuid4()))
    session.add(customer)
    session.commit()

    response = authenticated_client.get("/customers")
    assert response.status_code == 200
    assert response.is_json
    result = response.get_json()
    assert "data" in result
    assert "pagination" in result
    data = result["data"]
    assert isinstance(data, list)
    assert len(data) == 1
    assert result["pagination"]["total"] == 1
    assert data[0]["name"] == "Test Customer"


def test_get_customers_multiple(authenticated_client, session):
    """
    Test retrieving multiple customers.
    """
    customer1 = Customer(
        name="Customer One", company_id=1, contact_person="John Doe"
    )
    customer2 = Customer(name="Customer Two", company_id=1, email="a@a.a")
    session.add(customer1)
    session.add(customer2)
    session.commit()

    response = authenticated_client.get("/customers")
    assert response.status_code == 200
    assert response.is_json
    result = response.get_json()
    assert "data" in result
    assert "pagination" in result
    data = result["data"]
    assert isinstance(data, list)
    assert len(data) == 2
    assert result["pagination"]["total"] == 2
    assert data[0]["name"] == "Customer One"
    assert data[1]["name"] == "Customer Two"


def test_get_customers_content_type(authenticated_client):
    """
    Test the content type of the response for GET /customers.
    """
    response = authenticated_client.get("/customers")
    assert response.status_code == 200
    assert response.content_type == "application/json"


##################################################
# Test cases for POST /customers
##################################################
def test_post_customer_success(authenticated_client_with_company):
    """
    Test POST /customers with valid data.
    Should create a new customer and return 201 with the customer data.
    Note: company_id is extracted from JWT token, not from the payload.
    """
    # company_id is auto-assigned from JWT, not sent in payload
    payload = {"name": "Nouveau Client"}
    response = authenticated_client_with_company.post(
        "/customers", json=payload
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Nouveau Client"
    assert (
        data["company_id"] == authenticated_client_with_company.company_id
    )  # Auto-assigned from JWT
    assert "id" in data


def test_post_customer_missing_name(authenticated_client):
    """
    Test POST /customers with missing required 'name' field.
    Should return 400 with a validation error.
    """
    payload = {}
    response = authenticated_client.post("/customers", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "name" in data["error"]


def test_post_customer_unknown_field(authenticated_client):
    """
    Test POST /customers with an unknown field.
    Should return 400 with a validation error if unknown=RAISE in schema.
    """
    payload = {
        "name": "Client Mystère",
        "unknown_field": "valeur",
    }
    response = authenticated_client.post("/customers", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "unknown_field" in data["error"]


def test_post_customer_integrity_error(authenticated_client, monkeypatch):
    """
    Test POST /customers to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    setup_monkeypatch_integrity_error(monkeypatch)

    payload = {"name": "Test Client"}
    response = authenticated_client.post("/customers", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_post_customer_sqlalchemy_error(authenticated_client, monkeypatch):
    """
    Test POST /customers to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    setup_monkeypatch_sqlalchemy_error(monkeypatch)

    payload = {"name": "Test Client"}
    response = authenticated_client.post("/customers", json=payload)
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "database error" in data["error"].lower()


##################################################
# Test cases for GET /customers/<customer_id>
##################################################
def test_get_customer_by_id_success(authenticated_client, session):
    """
    Test GET /customers/<customer_id> with a valid ID.
    Should return the customer data and status 200.
    """
    customer_company_id = str(uuid.uuid4())
    customer = Customer(name="FindMe", company_id=customer_company_id)
    session.add(customer)
    session.commit()

    response = authenticated_client.get(f"/customers/{customer.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == customer.id
    assert data["name"] == "FindMe"
    assert data["company_id"] == customer_company_id


def test_get_customer_by_id_not_found(authenticated_client):
    """
    Test GET /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    response = authenticated_client.get("/customers/doesnotexist")
    assert response.status_code == 404
    data = response.get_json()
    assert "message" in data
    assert "not found" in data["message"].lower()


##################################################
# Test cases for PUT /customers/<customer_id>
##################################################
def test_put_customer_success(authenticated_client, session):
    """
    Test PUT /customers/<customer_id> with valid data.
    Should update the customer and return 200 with updated data.
    """
    customer_company_id = str(uuid.uuid4())
    customer = Customer(name="OldName", company_id=customer_company_id)
    session.add(customer)
    session.commit()

    payload = {"name": "NewName"}
    response = authenticated_client.put(
        f"/customers/{customer.id}", json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == customer.id
    assert data["name"] == "NewName"
    assert data["company_id"] == customer_company_id


def test_put_customer_not_found(authenticated_client):
    """
    Test PUT /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    payload = {"name": "DoesNotExist"}
    response = authenticated_client.put(
        "/customers/doesnotexist", json=payload
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_put_customer_missing_name(
    authenticated_client, test_customer_for_update
):
    """
    Test PUT /customers/<customer_id> with missing required 'name' field.
    Should return 400 with a validation error.
    """
    payload = {}
    response = authenticated_client.put(
        f"/customers/{test_customer_for_update.id}", json=payload
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "name" in data["error"]


def test_put_customer_unknown_field(
    authenticated_client, test_customer_for_update
):
    """
    Test PUT /customers/<customer_id> with an unknown field.
    Should return 400 with a validation error if unknown=RAISE in schema.
    """
    payload = {
        "name": "StillValid",
        "unknown_field": "should fail",
    }
    response = authenticated_client.put(
        f"/customers/{test_customer_for_update.id}", json=payload
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "unknown_field" in data["error"]


def test_put_customer_integrity_error(
    authenticated_client, test_customer_for_update, monkeypatch
):
    """
    Test PUT /customers/<customer_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    setup_monkeypatch_integrity_error(monkeypatch)

    payload = {"name": "NewName"}
    response = authenticated_client.put(
        f"/customers/{test_customer_for_update.id}", json=payload
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_put_customer_sqlalchemy_error(
    authenticated_client, test_customer_for_update, monkeypatch
):
    """
    Test PUT /customers/<customer_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    setup_monkeypatch_sqlalchemy_error(monkeypatch)

    payload = {"name": "NewName"}
    response = authenticated_client.put(
        f"/customers/{test_customer_for_update.id}", json=payload
    )
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "database error" in data["error"].lower()


##################################################
# Test cases for PATCH /customers/<customer_id>
##################################################


@pytest.fixture
def customer_fixture(session):
    """Fixture to create a customer for PATCH tests."""
    cust = Customer(name="PatchMe", company_id=str(uuid.uuid4()))
    session.add(cust)
    session.commit()
    return cust


def test_patch_customer_success(authenticated_client, customer_fixture):
    """
    Test PATCH /customers/<customer_id> with valid partial data.
    Should update only the provided fields and return 200.
    """
    payload = {"contact_person": "Jane Doe"}
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == customer_fixture.id
    assert data["contact_person"] == "Jane Doe"
    assert data["name"] == "PatchMe"  # unchanged


def test_patch_customer_not_found(authenticated_client):
    """
    Test PATCH /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    payload = {"contact_person": "Jane Doe"}
    response = authenticated_client.patch(
        "/customers/doesnotexist", json=payload
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_patch_customer_unknown_field(authenticated_client, customer_fixture):
    """
    Test PATCH /customers/<customer_id> with an unknown field.
    Should return 400 with a validation error.
    """
    payload = {"unknown_field": "should fail"}
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json=payload
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "unknown_field" in data["error"]


def test_patch_customer_name_too_long(authenticated_client, customer_fixture):
    """
    Test PATCH /customers/{id} with name exceeding maximum length.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json={"name": "a" * 101}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in data["error"]


def test_patch_customer_name_empty(authenticated_client, customer_fixture):
    """
    Test PATCH /customers/{id} with empty name.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json={"name": ""}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in data["error"]


def test_patch_customer_email_invalid(authenticated_client, customer_fixture):
    """
    Test PATCH /customers/{id} with invalid email format.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json={"email": "notanemail"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in data["error"]


def test_patch_customer_email_too_long(authenticated_client, customer_fixture):
    """
    Test PATCH /customers/{id} with email exceeding maximum length.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}",
        json={"email": "a@" + "b" * 100 + ".com"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in data["error"]


def test_patch_customer_contact_person_too_long(
    authenticated_client, customer_fixture
):
    """
    Test PATCH /customers/{id} with contact_person exceeding maximum length.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json={"contact_person": "a" * 101}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "contact_person" in data["error"]


def test_patch_customer_phone_number_too_long(
    authenticated_client, customer_fixture
):
    """
    Test PATCH /customers/{id} with phone_number exceeding maximum length.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json={"phone_number": "1" * 51}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "phone_number" in data["error"]


def test_patch_customer_phone_number_not_digits(
    authenticated_client, customer_fixture
):
    """
    Test PATCH /customers/{id} with phone_number containing non-digit characters.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json={"phone_number": "abc123"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "phone_number" in data["error"]


def test_patch_customer_address_too_long(
    authenticated_client, customer_fixture
):
    """
    Test PATCH /customers/{id} with address exceeding maximum length.
    """
    response = authenticated_client.patch(
        f"/customers/{customer_fixture.id}", json={"address": "a" * 256}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "address" in data["error"]


def test_patch_customer_integrity_error(
    authenticated_client, test_customer_for_update, monkeypatch
):
    """
    Test PATCH /customers/<customer_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    setup_monkeypatch_integrity_error(monkeypatch)

    payload = {"name": "NewName"}
    response = authenticated_client.patch(
        f"/customers/{test_customer_for_update.id}", json=payload
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_patch_customer_sqlalchemy_error(
    authenticated_client, test_customer_for_update, monkeypatch
):
    """
    Test PATCH /customers/<customer_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    setup_monkeypatch_sqlalchemy_error(monkeypatch)

    payload = {"name": "NewName"}
    response = authenticated_client.patch(
        f"/customers/{test_customer_for_update.id}", json=payload
    )
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "database error" in data["error"].lower()


##################################################
# Test cases for DELETE /customers/<customer_id>
##################################################
def test_delete_customer_success(
    authenticated_client, test_customer_for_update
):
    """
    Test DELETE /customers/<customer_id> with a valid ID.
    Should delete the customer and return 204.
    """
    response = authenticated_client.delete(
        f"/customers/{test_customer_for_update.id}"
    )
    assert response.status_code == 204
    # Optionally, check that the customer is really gone
    get_response = authenticated_client.get(
        f"/customers/{test_customer_for_update.id}"
    )
    assert get_response.status_code == 404


def test_delete_customer_not_found(authenticated_client):
    """
    Test DELETE /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    response = authenticated_client.delete("/customers/doesnotexist")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_delete_customer_integrity_error(
    authenticated_client, test_customer_for_update, monkeypatch
):
    """
    Test DELETE /customers/<customer_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    setup_monkeypatch_integrity_error(monkeypatch)

    response = authenticated_client.delete(
        f"/customers/{test_customer_for_update.id}"
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_delete_customer_sqlalchemy_error(
    authenticated_client, test_customer_for_update, monkeypatch
):
    """
    Test DELETE /customers/<customer_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    setup_monkeypatch_sqlalchemy_error(monkeypatch)

    response = authenticated_client.delete(
        f"/customers/{test_customer_for_update.id}"
    )
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "database error" in data["error"].lower()


######################################################
# Test cases for model methods
######################################################
def test_get_all_sqlalchemy_error(client, monkeypatch):
    """
    Test Customer.get_all() handles SQLAlchemyError gracefully.
    Should return an empty list and log the error.
    """
    _ = client  # Needed for Flask application context

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    # Patch sur la classe du query
    monkeypatch.setattr(type(Customer.query), "all", raise_sqlalchemy_error)
    result = Customer.get_all()
    assert result == []


def test_get_by_id_sqlalchemy_error(client, monkeypatch):
    """
    Test Customer.get_by_id() handles SQLAlchemyError gracefully.
    Should return None and log the error.
    """
    _ = client  # Needed for Flask application context

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    # Patch sur la classe du query
    monkeypatch.setattr(type(Customer.query), "get", raise_sqlalchemy_error)
    result = Customer.get_by_id("some-id")
    assert result is None


def test_get_by_company_id_sqlalchemy_error(client, monkeypatch):
    """
    Test Customer.get_by_company_id() handles SQLAlchemyError gracefully.
    Should return an empty list and log the error.
    """
    _ = client  # Needed for Flask application context

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    # On crée une instance factice avec une méthode all qui lève l'exception
    class FakeQuery:
        """Fake query object that raises SQLAlchemyError on all()."""

        def all(self):
            """Return all results, but raises SQLAlchemyError."""
            raise_sqlalchemy_error()

    monkeypatch.setattr(
        type(Customer.query), "filter_by", lambda *a, **k: FakeQuery()
    )
    result = Customer.get_by_company_id("some-company-id")
    assert result == []


def test_get_by_name_sqlalchemy_error(client, monkeypatch):
    """
    Test Customer.get_by_name() handles SQLAlchemyError gracefully.
    Should return None and log the error.
    """
    _ = client  # Needed for Flask application context

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    # On crée une instance factice avec une méthode first qui lève l'exception
    class FakeQuery:
        """Fake query object that raises SQLAlchemyError on first()."""

        def first(self):
            """Return first result, but raises SQLAlchemyError."""
            raise_sqlalchemy_error()

    monkeypatch.setattr(
        type(Customer.query), "filter_by", lambda *a, **k: FakeQuery()
    )
    result = Customer.get_by_name("some-name")
    assert result is None


def test_customer_repr():
    """
    Test the __repr__ method of the Customer model.
    """
    customer = Customer(
        id="1234",
        name="TestCustomer",
        email="test@example.com",
        company_id="5678",
    )
    repr_str = repr(customer)
    assert "TestCustomer" in repr_str
    assert "1234" in repr_str
    assert "test@example.com" in repr_str
    assert "5678" in repr_str
