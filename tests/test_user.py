"""
Test cases for the UserResource class in the PM Identity API.
"""
import uuid
import os
import jwt
from app.models.user import User
from app.models.company import Company


def get_init_db_payload():
    """
	Generate a valid payload for full database initialization via /init-db.
	Returns a dictionary containing data for company, organization_unit, position, and user.
	"""
    return {
		"company": {
			"name": "TestCorp",
			"description": "A test company"
		},
		"organization_unit": {
			"name": "Direction",
			"description": "Direction générale"
		},
		"position": {
			"title": "CEO",
			"description": "Chief Executive Officer"
		},
		"user": {
			"email": "admin@testcorp.com",
			"first_name": "Alice",
			"last_name": "Admin",
			"password": "supersecret"
		}
	}

def create_jwt_token(company_id, user_id):
    """Helper function to create a JWT token for testing."""
    jwt_secret = os.environ.get('JWT_SECRET', 'test_secret')
    payload = {
        "company_id": company_id,
        "user_id": user_id
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")

##################################################
# Test cases for GET /users
##################################################
def test_get_users_empty(client, session):
    """
    Test GET /users when there are no other users in the company.
    """
    # Create a company and user for authentication, but no other users
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    # Remove the user that was created by init-db to test empty state
    user = User.get_by_id(user_id)
    session.delete(user)
    session.commit()
    
    response = client.get('/users')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_get_users_single(client, session):
    """
    Test GET /users with a single user.
    """
    company_id = str(uuid.uuid4())
    user = User(
        email="test1@example.com",
        hashed_password="hashedpw1",
        first_name="Alice",
        last_name="Smith",
        company_id=company_id
    )
    session.add(user)
    session.commit()
    
    # Create JWT token for authentication
    jwt_token = create_jwt_token(company_id, str(user.id))
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    response = client.get('/users')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["email"] == "test1@example.com"
    assert data[0]["first_name"] == "Alice"
    assert data[0]["last_name"] == "Smith"
    assert data[0]["company_id"] == company_id
    assert "id" in data[0]

def test_get_users_multiple(client, session):
    """
    Test GET /users with multiple users.
    """
    company_id = str(uuid.uuid4())
    user1 = User(
        email="test2@example.com",
        hashed_password="hashedpw2",
        first_name="Bob",
        last_name="Jones",
        company_id=company_id
    )
    user2 = User(
        email="test3@example.com",
        hashed_password="hashedpw3",
        first_name="Carol",
        last_name="Brown",
        company_id=company_id
    )
    session.add_all([user1, user2])
    session.commit()
    
    # Create JWT token for authentication using the first user
    jwt_token = create_jwt_token(company_id, str(user1.id))
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    response = client.get('/users')
    assert response.status_code == 200
    data = response.get_json()
    emails = [item["email"] for item in data]
    assert "test2@example.com" in emails
    assert "test3@example.com" in emails
    first_names = [item["first_name"] for item in data]
    assert "Bob" in first_names
    assert "Carol" in first_names

##################################################
# Test cases for POST /users
##################################################

def test_post_user_success(client):
    """
    Test POST /users with valid data.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')

    payload = {
        "email": "newuser@example.com",
        "password": "MySecret123!",
        "first_name": "John",
        "last_name": "Doe",
        "company_id": company_id
    }
    response = client.post('/users', json=payload)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["email"] == "newuser@example.com"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["company_id"] == str(company_id)
    assert "id" in data

def test_post_user_missing_required_fields(client):
    """
    Test POST /users with missing required fields.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    payload = {
        "email": "nouser@example.com"
        # missing password, first_name, last_name, company_id
    }
    response = client.post('/users', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    # At least one required field should be mentioned in the error
    assert "password" in str(data).lower() or "first_name" in str(data).lower() or "last_name" in str(data).lower() or "company_id" in str(data).lower()

def test_post_user_duplicate_email(client, session):
    """
    Test POST /users with duplicate email.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    user = User(
        email="dup@example.com",
        hashed_password="hashedpw",
        first_name="Dup",
        last_name="User",
        company_id=company_id
    )
    session.add(user)
    session.commit()
    payload = {
        "email": "dup@example.com",
        "password": "AnotherSecret!",
        "first_name": "Dup",
        "last_name": "User",
        "company_id": company_id
    }
    response = client.post('/users', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in str(data).lower()

def test_post_user_invalid_email(client, session):
    """
    Test POST /users with invalid email format.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    payload = {
        "email": "not-an-email",
        "password": "Secret123!",
        "first_name": "Bad",
        "last_name": "Email",
        "company_id": company_id
    }
    response = client.post('/users', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in str(data).lower()

##################################################
# Test cases for GET /users/<id>
##################################################

def test_get_user_by_id_success(client, session):
    """
    Test GET /users/<id> for an existing user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    user = User(
        email="uniqueuser@example.com",
        hashed_password="hashedpw",
        first_name="Unique",
        last_name="User",
        company_id=company_id
    )
    session.add(user)
    session.commit()

    response = client.get(f'/users/{user.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == str(user.id)
    assert data["email"] == "uniqueuser@example.com"
    assert data["first_name"] == "Unique"
    assert data["last_name"] == "User"
    assert data["company_id"] == company_id

def test_get_user_by_id_not_found(client, session):
    """
    Test GET /users/<id> for a non-existent user.
    """
    fake_id = str(uuid.uuid4())
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    response = client.get(f'/users/{fake_id}')
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower() or "error" in data or "message" in data

##################################################
# Test cases for PUT /users/<id>
##################################################

def test_put_user_success(client, session):
    """
    Test PUT /users/<id> for a full update.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    user = User(
        email="old@example.com",
        hashed_password="oldhash",
        first_name="Old",
        last_name="Name",
        company_id=str(company_id)
    )
    session.add(user)
    session.commit()

    payload = {
        "email": "updated@example.com",
        "password": "NewSecret123!",
        "first_name": "Updated",
        "last_name": "User",
        "company_id": str(company_id)  # Keep same company to avoid security violation
    }
    response = client.put(f'/users/{user.id}', json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["id"] == str(user.id)
    assert data["email"] == "updated@example.com"
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "User"
    assert data["company_id"] == str(company_id)

def test_put_user_not_found(client, session):
    """
    Test PUT /users/<id> for a non-existent user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    fake_id = str(uuid.uuid4())
    payload = {
        "email": "nouser@example.com",
        "password": "Secret123!",
        "first_name": "No",
        "last_name": "User",
        "company_id": str(company_id)
    }
    response = client.put(f'/users/{fake_id}', json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower() or "error" in data or "message" in data

def test_put_user_missing_required_fields(client, session):
    """
    Test PUT /users/<id> with missing required fields.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    user = User(
        email="miss@example.com",
        hashed_password="hash",
        first_name="Miss",
        last_name="Field",
        company_id=str(company_id)
    )
    session.add(user)
    session.commit()
    payload = {
        "email": "miss2@example.com"
        # missing password, first_name, last_name, company_id
    }
    response = client.put(f'/users/{user.id}', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "password" in str(data).lower() or "first_name" in str(data).lower() or "last_name" in str(data).lower() or "company_id" in str(data).lower()

##################################################
# Test cases for PATCH /users/<id>
##################################################

def test_patch_user_success(client, session):
    """
    Test PATCH /users/<id> for a partial update.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    user = User(
        email="patchme@example.com",
        hashed_password="oldhash",
        first_name="Patch",
        last_name="User",
        company_id=str(company_id)
    )
    session.add(user)
    session.commit()

    payload = {
        "first_name": "Patched",
        "last_name": "UserUpdated"
    }
    response = client.patch(f'/users/{user.id}', json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["first_name"] == "Patched"
    assert data["last_name"] == "UserUpdated"
    assert data["email"] == "patchme@example.com"

def test_patch_user_not_found(client, session):
    """
    Test PATCH /users/<id> for a non-existent user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    fake_id = str(uuid.uuid4())
    payload = {"first_name": "Ghost"}
    response = client.patch(f'/users/{fake_id}', json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower() or "error" in data or "message" in data

def test_patch_user_invalid_email(client, session):
    """
    Test PATCH /users/<id> with invalid email format.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    user = User(
        email="patchmail@example.com",
        hashed_password="hash",
        first_name="PatchMail",
        last_name="User",
        company_id=str(company_id)
    )
    session.add(user)
    session.commit()
    payload = {"email": "not-an-email"}
    response = client.patch(f'/users/{user.id}', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in str(data).lower()

##################################################
# Test cases for DELETE /users/<id>
##################################################

def test_delete_user_success(client, session):
    """
    Test DELETE /users/<id> for an existing user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    user = User(
        email="delete@example.com",
        hashed_password="hash",
        first_name="Del",
        last_name="User",
        company_id=str(company_id)
    )
    session.add(user)
    session.commit()

    response = client.delete(f'/users/{user.id}')
    assert response.status_code == 204

    # Vérifie que l'utilisateur n'existe plus
    get_response = client.get(f'/users/{user.id}')
    assert get_response.status_code == 404

def test_delete_user_not_found(client, session):
    """
    Test DELETE /users/<id> for a non-existent user.
    """
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie('access_token', jwt_token, domain='localhost')
    
    fake_id = str(uuid.uuid4())
    response = client.delete(f'/users/{fake_id}')
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower() or "error" in data or "message" in data

##################################################
# Test cases for GET /company/<string:company_id>/users
##################################################

def test_get_users_by_company(client, session):
    """
    Test GET /companies/<company_id>/users returns only users for the given company.
    """
    company1 = Company(name="CompA")
    company2 = Company(name="CompB")
    session.add_all([company1, company2])
    session.commit()
    user1 = User(email="a@a.com", hashed_password="hash", first_name="A", last_name="A", company_id=str(company1.id))
    user2 = User(email="b@b.com", hashed_password="hash", first_name="B", last_name="B", company_id=str(company2.id))
    session.add_all([user1, user2])
    session.commit()

    response = client.get(f'/companies/{company1.id}/users')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["email"] == "a@a.com"

##################################################
# Test cases for POST /company/<string:company_id>/users
##################################################

def test_post_user_for_company_success(client, session):
    """
    Test POST /companies/<company_id>/users with valid data.
    """
    company = Company(name="CompanyPost")
    session.add(company)
    session.commit()
    payload = {
        "email": "companyuser@example.com",
        "password": "Secret123!",
        "first_name": "Comp",
        "last_name": "User"
    }
    response = client.post(f'/companies/{company.id}/users', json=payload)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["email"] == "companyuser@example.com"
    assert data["first_name"] == "Comp"
    assert data["last_name"] == "User"
    assert data["company_id"] == str(company.id)
    assert "id" in data

def test_post_user_for_company_missing_fields(client, session):
    """
    Test POST /companies/<company_id>/users with missing required fields.
    """
    company = Company(name="CompanyPost2")
    session.add(company)
    session.commit()
    payload = {
        "email": "missingfields@example.com"
        # missing password, first_name, last_name
    }
    response = client.post(f'/companies/{company.id}/users', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "password" in str(data).lower() or "first_name" in str(data).lower() or "last_name" in str(data).lower()

def test_post_user_for_company_invalid_email(client, session):
    """
    Test POST /companies/<company_id>/users with invalid email.
    """
    company = Company(name="CompanyPost3")
    session.add(company)
    session.commit()
    payload = {
        "email": "not-an-email",
        "password": "Secret123!",
        "first_name": "Comp",
        "last_name": "User"
    }
    response = client.post(f'/companies/{company.id}/users', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in str(data).lower()

def test_post_user_for_company_not_found(client, session):
    """
    Test POST /companies/<company_id>/users with non-existent company.
    """
    fake_company_id = str(uuid.uuid4())
    payload = {
        "email": "nouser@example.com",
        "password": "Secret123!",
        "first_name": "Ghost",
        "last_name": "User"
    }
    response = client.post(f'/companies/{fake_company_id}/users', json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower() or "company" in str(data).lower()

##################################################
# Test cases for DELETE /company/<string:company_id>/users
##################################################

def test_delete_users_by_company_success(client, session):
    """
    Test DELETE /companies/<company_id>/users supprime tous les utilisateurs de la société.
    """
    company = Company(name="DeleteCompany")
    session.add(company)
    session.commit()
    user1 = User(email="del1@example.com", hashed_password="hash", first_name="Del1", last_name="User1", company_id=str(company.id))
    user2 = User(email="del2@example.com", hashed_password="hash", first_name="Del2", last_name="User2", company_id=str(company.id))
    session.add_all([user1, user2])
    session.commit()

    response = client.delete(f'/companies/{company.id}/users')
    assert response.status_code == 204

    # Vérifie qu'il n'y a plus d'utilisateurs pour cette société
    get_response = client.get(f'/companies/{company.id}/users')
    assert get_response.status_code == 200
    data = get_response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_delete_users_by_company_not_found(client, session):
    """
    Test DELETE /company/<company_id>/users pour une société inexistante.
    """
    fake_company_id = str(uuid.uuid4())
    response = client.delete(f'/company/{fake_company_id}/users')
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in str(data).lower() or "company" in str(data).lower()

##################################################
# Test cases for GET /position/<string:position_id>/users
##################################################

def test_get_users_by_position(client, session):
    """
    Test GET /positions/<position_id>/users returns only users for the given position.
    """
    company = Company(name="PosCo")
    session.add(company)
    session.commit()

    position1_id = str(uuid.uuid4())
    position2_id = str(uuid.uuid4())

    user1 = User(
        email="pos1@example.com",
        hashed_password="hash",
        first_name="Pos1",
        last_name="User1",
        company_id=str(company.id),
        position_id=position1_id
    )
    user2 = User(
        email="pos2@example.com",
        hashed_password="hash",
        first_name="Pos2",
        last_name="User2",
        company_id=str(company.id),
        position_id=position2_id
    )
    user3 = User(
        email="nopos@example.com",
        hashed_password="hash",
        first_name="NoPos",
        last_name="User3",
        company_id=str(company.id),
        position_id=None
    )
    session.add_all([user1, user2, user3])
    session.commit()

    response = client.get(f'/positions/{position1_id}/users')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["email"] == "pos1@example.com"

    response2 = client.get(f'/positions/{position2_id}/users')
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, list)
    assert len(data2) == 1
    assert data2[0]["email"] == "pos2@example.com"

def test_get_users_by_position_not_found(client):
    """
    Test GET /positions/<position_id>/users for a position with no users.
    """
    fake_position_id = str(uuid.uuid4())
    response = client.get(f'/positions/{fake_position_id}/users')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0

##################################################
# Test cases for POST /verify_password
##################################################

from werkzeug.security import generate_password_hash

def test_verify_password_success(client, session):
    """
    Test POST /verify_password with correct email and password.
    """
    company_id = str(uuid.uuid4())
    password = "MySecret123!"
    user = User(
        email="verify@example.com",
        hashed_password=generate_password_hash(password),
        first_name="Veri",
        last_name="Fy",
        company_id=company_id
    )
    session.add(user)
    session.commit()

    payload = {"email": "verify@example.com", "password": password}
    response = client.post('/verify_password', json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["email"] == "verify@example.com"

def test_verify_password_wrong_password(client, session):
    """
    Test POST /verify_password with wrong password.
    """
    company_id = str(uuid.uuid4())
    user = User(
        email="wrongpw@example.com",
        hashed_password=generate_password_hash("RightPassword!"),
        first_name="Wrong",
        last_name="PW",
        company_id=company_id
    )
    session.add(user)
    session.commit()

    payload = {"email": "wrongpw@example.com", "password": "WrongPassword!"}
    response = client.post('/verify_password', json=payload)
    assert response.status_code == 403
    data = response.get_json()
    assert "invalid" in str(data).lower()

def test_verify_password_user_not_found(client, session):
    """
    Test POST /verify_password with non-existent user.
    """
    payload = {"email": "notfound@example.com", "password": "AnyPassword"}
    response = client.post('/verify_password', json=payload)
    assert response.status_code == 403
    data = response.get_json()
    assert "invalid" in str(data).lower()

def test_verify_password_missing_password(client, session):
    """
    Test POST /verify_password with missing password field.
    """
    company_id = str(uuid.uuid4())
    user = User(
        email="nopw@example.com",
        hashed_password=generate_password_hash("SomePassword!"),
        first_name="No",
        last_name="PW",
        company_id=company_id
    )
    session.add(user)
    session.commit()

    payload = {"email": "nopw@example.com"}
    response = client.post('/verify_password', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "required" in str(data).lower()
