"""
Test cases for the /companies endpoint in the Flask application.
These tests cover various scenarios for retrieving company data, including
empty responses, single company retrieval, multiple companies, and content 
type checks.
"""
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.company import Company

##################################################
# Test cases for GET /companies
##################################################
def test_get_companies_empty(client):
    """
    Test GET /companies when there are no companies in the database.
    Should return an empty list and status 200.
    """
    response = client.get('/companies')
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == []

def test_get_companies_single(client, session):
    """
    Test GET /companies when there is a single company.
    Should return a list with one company.
    """
    company = Company(
        name="Test Company",
        description="A test company",
        city="Paris"
    )
    session.add(company)
    session.commit()

    response = client.get('/companies')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['name'] == "Test Company"
    assert data[0]['description'] == "A test company"
    assert data[0]['city'] == "Paris"
    assert 'id' in data[0]

def test_get_companies_multiple(client, session):
    """
    Test GET /companies when there are multiple companies.
    Should return a list with all companies.
    """
    companies = [
        Company(name="Company A"),
        Company(name="Company B", city="Lyon"),
        Company(name="Company C", country="France"),
    ]
    session.add_all(companies)
    session.commit()

    response = client.get('/companies')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 3

    names = [c['name'] for c in data]
    assert "Company A" in names
    assert "Company B" in names
    assert "Company C" in names

def test_get_companies_content_type(client):
    """
    Test GET /companies returns the correct Content-Type header.
    """
    response = client.get('/companies')
    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('application/json')

######################################################
# Test cases for POST /companies
######################################################
def test_post_company_success(client):
    """
    Test POST /companies with valid data.
    Should create a new company and return 201 with the company data.
    """
    payload = {
        "name": "Nouvelle Société",
        "description": "Entreprise de test",
        "city": "Paris"
    }
    response = client.post('/companies', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Nouvelle Société"
    assert data["description"] == "Entreprise de test"
    assert data["city"] == "Paris"
    assert "id" in data

def test_post_company_missing_name(client):
    """
    Test POST /companies with missing required 'name' field.
    Should return 400 with a validation error.
    """
    payload = {
        "description": "Entreprise sans nom"
    }
    response = client.post('/companies', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "name" in data["errors"]

def test_post_company_unknown_field(client):
    """
    Test POST /companies with an unknown field.
    Should return 400 with a validation error if unknown=RAISE in schema.
    """
    payload = {
        "name": "Société Mystère",
        "unknown_field": "valeur"
    }
    response = client.post('/companies', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "unknown_field" in data["errors"]

def test_post_company_duplicate_name(client, session):
    """
    Test POST /companies with a duplicate name.
    Should return 400 with an integrity error.
    """
    company = Company(name="UniqueName")
    session.add(company)
    session.commit()

    payload = {
        "name": "UniqueName"
    }
    response = client.post('/companies', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "message" in data
    assert "Integrity error" in data["message"] or "unique" in data.get("errors", {}).get("name", [""])[0].lower()

def test_post_integrity_error(client, monkeypatch):
    """
    Test POST /companies to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    response = client.post('/companies', json={'name': 'Test Company'})
    assert response.status_code == 400


def test_post_sqlalchemy_error(client, monkeypatch):
    """
    Test POST /companies to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    response = client.post('/companies', json={'name': 'Test Company'})
    assert response.status_code == 500

######################################################
# Test cases for GET /companies/<company_id>
######################################################
def test_get_company_by_id_success(client, session):
    """
    Test GET /companies/<company_id> with a valid ID.
    Should return the company data and status 200.
    """
    company = Company(name="FindMe", description="To be found")
    session.add(company)
    session.commit()

    response = client.get(f"/companies/{company.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == company.id
    assert data["name"] == "FindMe"
    assert data["description"] == "To be found"

def test_get_company_by_id_not_found(client):
    """
    Test GET /companies/<company_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    response = client.get("/companies/doesnotexist")
    assert response.status_code == 404
    data = response.get_json()
    assert "message" in data
    assert "not found" in data["message"].lower()

######################################################
# Test cases for PUT /companies/<company_id>
######################################################
def test_put_company_success(client, session):
    """
    Test PUT /companies/<company_id> with valid data.
    Should update the company and return 200 with updated data.
    """
    company = Company(name="OldName", description="Old desc")
    session.add(company)
    session.commit()

    payload = {
        "name": "NewName",
        "description": "New description",
        "city": "Lyon"
    }
    response = client.put(f"/companies/{company.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == company.id
    assert data["name"] == "NewName"
    assert data["description"] == "New description"
    assert data["city"] == "Lyon"

def test_put_company_not_found(client):
    """
    Test PUT /companies/<company_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    payload = {"name": "DoesNotExist"}
    response = client.put("/companies/doesnotexist", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "message" in data
    assert "not found" in data["message"].lower()

def test_put_company_missing_name(client, session):
    """
    Test PUT /companies/<company_id> with missing required 'name' field.
    Should return 400 with a validation error.
    """
    company = Company(name="ToBeUpdated")
    session.add(company)
    session.commit()

    payload = {"description": "No name provided"}
    response = client.put(f"/companies/{company.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "name" in data["errors"]

def test_put_company_unknown_field(client, session):
    """
    Test PUT /companies/<company_id> with an unknown field.
    Should return 400 with a validation error if unknown=RAISE in schema.
    """
    company = Company(name="ToBeUpdated")
    session.add(company)
    session.commit()

    payload = {
        "name": "StillValid",
        "unknown_field": "should fail"
    }
    response = client.put(f"/companies/{company.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "unknown_field" in data["errors"]

def test_put_company_duplicate_name(client, session):
    """
    Test PUT /companies/<company_id> with a duplicate name.
    Should return 400 with an integrity error.
    """
    company1 = Company(name="FirstCompany")
    company2 = Company(name="SecondCompany")
    session.add_all([company1, company2])
    session.commit()

    payload = {"name": "FirstCompany"}
    response = client.put(f"/companies/{company2.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "message" in data or "errors" in data

def test_put_company_integrity_error(client, session, monkeypatch):
    """
    Test PUT /companies/<company_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    company = Company(name="ToBeUpdated")
    session.add(company)
    session.commit()

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    payload = {"name": "NewName"}
    response = client.put(f"/companies/{company.id}", json=payload)
    assert response.status_code == 400

def test_put_company_sqlalchemy_error(client, session, monkeypatch):
    """
    Test PUT /companies/<company_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    company = Company(name="ToBeUpdated")
    session.add(company)
    session.commit()

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    payload = {"name": "NewName"}
    response = client.put(f"/companies/{company.id}", json=payload)
    assert response.status_code == 500

######################################################
# Test cases for PATCH /companies/<company_id>
######################################################
def test_patch_company_success(client, session):
    """
    Test PATCH /companies/<company_id> with valid partial data.
    Should update only the provided fields and return 200.
    """
    company = Company(name="PatchMe", description="Old desc", city="Paris")
    session.add(company)
    session.commit()

    payload = {
        "description": "New desc"
    }
    response = client.patch(f"/companies/{company.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == company.id
    assert data["name"] == "PatchMe"
    assert data["description"] == "New desc"
    assert data["city"] == "Paris"  # unchanged

def test_patch_company_not_found(client):
    """
    Test PATCH /companies/<company_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    payload = {"description": "Does not matter"}
    response = client.patch("/companies/doesnotexist", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "message" in data
    assert "not found" in data["message"].lower()

def test_patch_company_unknown_field(client, session):
    """
    Test PATCH /companies/<company_id> with an unknown field.
    Should return 400 with a validation error if unknown=RAISE in schema.
    """
    company = Company(name="PatchMe")
    session.add(company)
    session.commit()

    payload = {
        "unknown_field": "should fail"
    }
    response = client.patch(f"/companies/{company.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "unknown_field" in data["errors"]

def test_patch_company_integrity_error(client, session, monkeypatch):
    """
    Test PATCH /companies/<company_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    company = Company(name="PatchMe")
    session.add(company)
    session.commit()

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    payload = {"description": "New desc"}
    response = client.patch(f"/companies/{company.id}", json=payload)
    assert response.status_code == 400

def test_patch_company_sqlalchemy_error(client, session, monkeypatch):
    """
    Test PATCH /companies/<company_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    company = Company(name="PatchMe")
    session.add(company)
    session.commit()

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    payload = {"description": "New desc"}
    response = client.patch(f"/companies/{company.id}", json=payload)
    assert response.status_code == 500

######################################################
# Test cases for DELETE /companies/<company_id>
######################################################
def test_delete_company_success(client, session):
    """
    Test DELETE /companies/<company_id> with a valid ID.
    Should delete the company and return 204.
    """
    company = Company(name="DeleteMe")
    session.add(company)
    session.commit()

    response = client.delete(f"/companies/{company.id}")
    assert response.status_code == 204
    # Optionally, check that the company is really gone
    get_response = client.get(f"/companies/{company.id}")
    assert get_response.status_code == 404

def test_delete_company_not_found(client):
    """
    Test DELETE /companies/<company_id> with a non-existent ID.
    Should return 404 and an error message.
    """
    response = client.delete("/companies/doesnotexist")
    assert response.status_code == 404
    data = response.get_json()
    assert "message" in data
    assert "not found" in data["message"].lower()

def test_delete_company_integrity_error(client, session, monkeypatch):
    """
    Test DELETE /companies/<company_id> to simulate an IntegrityError.
    Should return 400 with an integrity error message.
    """
    company = Company(name="DeleteMe")
    session.add(company)
    session.commit()

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("Mocked IntegrityError", None, None)

    monkeypatch.setattr("app.models.db.session.commit", raise_integrity_error)

    response = client.delete(f"/companies/{company.id}")
    assert response.status_code == 400

def test_delete_company_sqlalchemy_error(client, session, monkeypatch):
    """
    Test DELETE /companies/<company_id> to simulate a SQLAlchemyError.
    Should return 500 with an error message.
    """
    company = Company(name="DeleteMe")
    session.add(company)
    session.commit()

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr("app.models.db.session.commit", raise_sqlalchemy_error)

    response = client.delete(f"/companies/{company.id}")
    assert response.status_code == 500

######################################################
# Test cases for model methods
######################################################
def test_get_all_sqlalchemy_error(client, monkeypatch):
    """
    Test Company.get_all() handles SQLAlchemyError gracefully.
    Should return an empty list and log the error.
    """
    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr(Company.query, "all", raise_sqlalchemy_error)
    result = Company.get_all()
    assert result == []

def test_get_by_id_sqlalchemy_error(client, monkeypatch):
    """
    Test Company.get_by_id() handles SQLAlchemyError gracefully.
    Should return None and log the error.
    """
    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr(Company.query, "get", raise_sqlalchemy_error)
    result = Company.get_by_id("some-id")
    assert result is None

def test_get_by_name_sqlalchemy_error(client, monkeypatch):
    """
    Test Company.get_by_name() handles SQLAlchemyError gracefully.
    Should return None and log the error.
    """
    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("Mocked SQLAlchemyError")

    monkeypatch.setattr(Company.query, "filter_by", lambda *a, **k: type("Q", (), {"first": raise_sqlalchemy_error})())
    result = Company.get_by_name("some-name")
    assert result is None

def test_company_repr():
    """
    Test the __repr__ method of the Company model.
    """
    company = Company(
        id="1234",
        name="TestCo",
        description="A test company"
    )
    repr_str = repr(company)
    assert "<Company TestCo>" in repr_str
    assert "ID: 1234" in repr_str
    assert "Description: A test company" in repr_str
