"""
Test cases for the Customer resource in the PM Identity API.
"""

import uuid
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.customer import Customer
from tests.conftest import create_jwt_token


##################################################
# Test cases for GET /customers
##################################################
def test_get_all_customers(client):
    """
    Test retrieving all customers.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.get("/customers")
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert response.is_json
    assert response.get_json() == []


def test_get_customers_single(client, session):
    """
    Test retrieving a single customer by ID.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="Test Customer", company_id=1)
    session.add(customer)
    session.commit()

    response = client.get("/customers")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "Test Customer"


def test_get_customers_multiple(client, session):
    """
    Test retrieving multiple customers.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer1 = Customer(
        name="Customer One", company_id=1, contact_person="John Doe"
    )
    customer2 = Customer(name="Customer Two", company_id=1, email="a@a.a")
    session.add(customer1)
    session.add(customer2)
    session.commit()

    response = client.get("/customers")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "Customer One"
    assert data[1]["name"] == "Customer Two"


def test_get_customers_content_type(client):
    """
    Test the content type of the response for GET /customers.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.get("/customers")
    assert response.status_code == 200
    assert response.content_type == "application/json"


##################################################
# Test cases for POST /customers
##################################################
def test_post_customer_success(client):
    """
    Test POST /customers with valid data.
    Should create a new customer and return 201 with the customer data.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    payload = {"name": "Nouveau Client", "company_id": 1}
    response = client.post("/customers", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Nouveau Client"
    assert data["company_id"] == 1
    assert "id" in data


def test_post_customer_missing_name(client):
    """
    Test POST /customers with missing required 'name' field.
    Should return 400 with a validation error.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    payload = {"company_id": 1}
    response = client.post("/customers", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "name" in data["error"]


def test_post_customer_unknown_field(client):
    """
    Test POST /customers with an unknown field.
    Should return 400 with a validation error if unknown=RAISE in schema.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    payload = {
        "name": "Client Mystère",
        "company_id": 1,
        "unknown_field": "valeur",
    }
    response = client.post("/customers", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "unknown_field" in data["error"]


def test_post_customer_integrity_error(client, monkeypatch):
    """
    Test POST /customers to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    payload = {"name": "Test Client", "company_id": 1}
    response = client.post("/customers", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_post_customer_sqlalchemy_error(client, monkeypatch):
    """
    Test POST /customers to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    payload = {"name": "Test Client", "company_id": 1}
    response = client.post("/customers", json=payload)
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "database error" in data["error"].lower()


##################################################
# Test cases for GET /customers/<customer_id>
##################################################
def test_get_customer_by_id_success(client, session):
    """
    Test GET /customers/<customer_id> with a valid ID.
    Should return the customer data and status 200.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="FindMe", company_id=1)
    session.add(customer)
    session.commit()

    response = client.get(f"/customers/{customer.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == customer.id
    assert data["name"] == "FindMe"
    assert data["company_id"] == 1


def test_get_customer_by_id_not_found(client):
    """
    Test GET /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.get("/customers/doesnotexist")
    assert response.status_code == 404
    data = response.get_json()
    assert "message" in data
    assert "not found" in data["message"].lower()


##################################################
# Test cases for PUT /customers/<customer_id>
##################################################
def test_put_customer_success(client, session):
    """
    Test PUT /customers/<customer_id> with valid data.
    Should update the customer and return 200 with updated data.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="OldName", company_id=1)
    session.add(customer)
    session.commit()

    payload = {"name": "NewName", "company_id": 1}
    response = client.put(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == customer.id
    assert data["name"] == "NewName"
    assert data["company_id"] == 1


def test_put_customer_not_found(client):
    """
    Test PUT /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    payload = {"name": "DoesNotExist", "company_id": 1}
    response = client.put("/customers/doesnotexist", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_put_customer_missing_name(client, session):
    """
    Test PUT /customers/<customer_id> with missing required 'name' field.
    Should return 400 with a validation error.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="ToBeUpdated", company_id=1)
    session.add(customer)
    session.commit()

    payload = {"company_id": 1}
    response = client.put(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "name" in data["error"]


def test_put_customer_unknown_field(client, session):
    """
    Test PUT /customers/<customer_id> with an unknown field.
    Should return 400 with a validation error if unknown=RAISE in schema.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="ToBeUpdated", company_id=1)
    session.add(customer)
    session.commit()

    payload = {
        "name": "StillValid",
        "company_id": 1,
        "unknown_field": "should fail",
    }
    response = client.put(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "unknown_field" in data["error"]


def test_put_customer_integrity_error(client, session, monkeypatch):
    """
    Test PUT /customers/<customer_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="ToBeUpdated", company_id=1)
    session.add(customer)
    session.commit()

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    payload = {"name": "NewName", "company_id": 1}
    response = client.put(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_put_customer_sqlalchemy_error(client, session, monkeypatch):
    """
    Test PUT /customers/<customer_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="ToBeUpdated", company_id=1)
    session.add(customer)
    session.commit()

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    payload = {"name": "NewName", "company_id": 1}
    response = client.put(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "database error" in data["error"].lower()


##################################################
# Test cases for PATCH /customers/<customer_id>
##################################################
import pytest


@pytest.fixture
def customer(session):
    c = Customer(name="PatchMe", company_id=1)
    session.add(c)
    session.commit()
    return c


def test_patch_customer_success(client, session, customer):
    """
    Test PATCH /customers/<customer_id> with valid partial data.
    Should update only the provided fields and return 200.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    payload = {"contact_person": "Jane Doe"}
    response = client.patch(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == customer.id
    assert data["contact_person"] == "Jane Doe"
    assert data["name"] == "PatchMe"  # unchanged


def test_patch_customer_not_found(client):
    """
    Test PATCH /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    payload = {"contact_person": "Jane Doe"}
    response = client.patch("/customers/doesnotexist", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_patch_customer_unknown_field(client, session, customer):
    """
    Test PATCH /customers/<customer_id> with an unknown field.
    Should return 400 with a validation error.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    payload = {"unknown_field": "should fail"}
    response = client.patch(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "unknown_field" in data["error"]


def test_patch_customer_name_too_long(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"name": "a" * 101}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in data["error"]


def test_patch_customer_name_empty(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(f"/customers/{customer.id}", json={"name": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in data["error"]


def test_patch_customer_email_invalid(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"email": "notanemail"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in data["error"]


def test_patch_customer_email_too_long(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"email": "a@" + "b" * 100 + ".com"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in data["error"]


def test_patch_customer_contact_person_too_long(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"contact_person": "a" * 101}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "contact_person" in data["error"]


def test_patch_customer_phone_number_too_long(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"phone_number": "1" * 51}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "phone_number" in data["error"]


def test_patch_customer_phone_number_not_digits(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"phone_number": "abc123"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "phone_number" in data["error"]


def test_patch_customer_address_too_long(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"address": "a" * 256}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "address" in data["error"]


def test_patch_customer_company_id_invalid(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"company_id": 0}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "company_id" in data["error"]


def test_patch_customer_company_id_not_int(client, session, customer):
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.patch(
        f"/customers/{customer.id}", json={"company_id": "notanint"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "company_id" in data["error"]


def test_patch_customer_integrity_error(client, session, monkeypatch):
    """
    Test PATCH /customers/<customer_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="ToBeUpdated", company_id=1)
    session.add(customer)
    session.commit()

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    payload = {"name": "NewName", "company_id": 1}
    response = client.patch(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_patch_customer_sqlalchemy_error(client, session, monkeypatch):
    """
    Test PATCH /customers/<customer_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="ToBeUpdated", company_id=1)
    session.add(customer)
    session.commit()

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    payload = {"name": "NewName", "company_id": 1}
    response = client.patch(f"/customers/{customer.id}", json=payload)
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "database error" in data["error"].lower()


##################################################
# Test cases for DELETE /customers/<customer_id>
##################################################
def test_delete_customer_success(client, session):
    """
    Test DELETE /customers/<customer_id> with a valid ID.
    Should delete the customer and return 204.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="DeleteMe", company_id=1)
    session.add(customer)
    session.commit()

    response = client.delete(f"/customers/{customer.id}")
    assert response.status_code == 204
    # Optionally, check that the customer is really gone
    get_response = client.get(f"/customers/{customer.id}")
    assert get_response.status_code == 404


def test_delete_customer_not_found(client):
    """
    Test DELETE /customers/<customer_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.delete("/customers/doesnotexist")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_delete_customer_integrity_error(client, session, monkeypatch):
    """
    Test DELETE /customers/<customer_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="DeleteMe", company_id=1)
    session.add(customer)
    session.commit()

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    response = client.delete(f"/customers/{customer.id}")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "integrity error" in data["error"].lower()


def test_delete_customer_sqlalchemy_error(client, session, monkeypatch):
    """
    Test DELETE /customers/<customer_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    customer = Customer(name="DeleteMe", company_id=1)
    session.add(customer)
    session.commit()

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    response = client.delete(f"/customers/{customer.id}")
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
    _ = client

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
    _ = client

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
    _ = client

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    # On crée une instance factice avec une méthode all qui lève l'exception
    class FakeQuery:
        def all(self):
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
    _ = client

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    # On crée une instance factice avec une méthode first qui lève l'exception
    class FakeQuery:
        def first(self):
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
