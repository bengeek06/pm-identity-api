# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Test cases for search functionality across all collection endpoints.
"""

import uuid

from app.models.company import Company
from app.models.customer import Customer
from app.models.organization_unit import OrganizationUnit
from app.models.position import Position
from app.models.subcontractor import Subcontractor
from app.models.user import User
from tests.unit.conftest import create_jwt_token


##################################################
# Position Search Tests
##################################################
def test_search_positions_by_title(client, session):
    """Test searching positions by title."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="TestUnit", company_id=company_id)
    session.add(unit)
    session.commit()

    pos1 = Position(
        title="Senior Developer",
        description="Python expert",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    pos2 = Position(
        title="Junior Developer",
        description="Learning Java",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    pos3 = Position(
        title="Product Manager",
        description="Agile methodology",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    session.add_all([pos1, pos2, pos3])
    session.commit()

    # Search for "Developer" - should match 2 positions
    response = client.get("/positions?search=Developer")
    assert response.status_code == 200
    result = response.get_json()
    assert "data" in result
    data = result["data"]
    assert len(data) == 2
    assert result["pagination"]["total"] == 2
    titles = [item["title"] for item in data]
    assert "Senior Developer" in titles
    assert "Junior Developer" in titles


def test_search_positions_by_description(client, session):
    """Test searching positions by description."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="TestUnit", company_id=company_id)
    session.add(unit)
    session.commit()

    pos1 = Position(
        title="Developer",
        description="Python expert",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    pos2 = Position(
        title="Developer",
        description="Java expert",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    session.add_all([pos1, pos2])
    session.commit()

    # Search for "Python" in description
    response = client.get("/positions?search=Python")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 1
    assert result["data"][0]["description"] == "Python expert"


def test_search_positions_case_insensitive(client, session):
    """Test that position search is case insensitive."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="TestUnit", company_id=company_id)
    session.add(unit)
    session.commit()

    pos = Position(
        title="Senior Developer",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    session.add(pos)
    session.commit()

    # Search with lowercase
    response = client.get("/positions?search=developer")
    assert response.status_code == 200
    assert len(response.get_json()["data"]) == 1


##################################################
# User Search Tests
##################################################
def test_search_users_by_email(client, session):
    """Test searching users by email."""
    company_id = str(uuid.uuid4())
    user1 = User(
        email="alice@example.com",
        hashed_password="hash1",
        first_name="Alice",
        last_name="Smith",
        company_id=company_id,
    )
    user2 = User(
        email="bob@example.com",
        hashed_password="hash2",
        first_name="Bob",
        last_name="Jones",
        company_id=company_id,
    )
    session.add_all([user1, user2])
    session.commit()

    jwt_token = create_jwt_token(company_id, str(user1.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get("/users?search=alice")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 1
    assert result["data"][0]["email"] == "alice@example.com"


def test_search_users_by_name(client, session):
    """Test searching users by first or last name."""
    company_id = str(uuid.uuid4())
    user1 = User(
        email="alice@example.com",
        hashed_password="hash1",
        first_name="Alice",
        last_name="Smith",
        company_id=company_id,
    )
    user2 = User(
        email="bob@example.com",
        hashed_password="hash2",
        first_name="Bob",
        last_name="Smith",
        company_id=company_id,
    )
    session.add_all([user1, user2])
    session.commit()

    jwt_token = create_jwt_token(company_id, str(user1.id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Search by last name
    response = client.get("/users?search=Smith")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 2
    assert result["pagination"]["total"] == 2


##################################################
# Company Search Tests
##################################################
def test_search_companies_by_name(client, session):
    """Test searching companies by name."""
    company1 = Company(name="Acme Corp", description="Manufacturing")
    company2 = Company(name="Acme Solutions", description="IT Services")
    company3 = Company(name="Beta Inc", description="Consulting")
    session.add_all([company1, company2, company3])
    session.commit()

    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get("/companies?search=Acme")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 2
    assert result["pagination"]["total"] == 2


def test_search_companies_by_description(client, session):
    """Test searching companies by description."""
    company1 = Company(name="Company A", description="IT Services")
    company2 = Company(name="Company B", description="Manufacturing")
    session.add_all([company1, company2])
    session.commit()

    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get("/companies?search=IT")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "Company A"


##################################################
# Organization Unit Search Tests
##################################################
def test_search_organization_units_by_name(client, session):
    """Test searching organization units by name."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit1 = OrganizationUnit(
        name="Engineering Team", description="Software", company_id=company_id
    )
    unit2 = OrganizationUnit(
        name="Sales Team", description="Revenue", company_id=company_id
    )
    session.add_all([unit1, unit2])
    session.commit()

    response = client.get("/organization_units?search=Team")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 2


##################################################
# Customer Search Tests
##################################################
def test_search_customers_by_name(client, session):
    """Test searching customers by name."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    customer1 = Customer(
        name="Acme Industries",
        email="contact@acme.com",
        company_id=company_id,
    )
    customer2 = Customer(
        name="Beta Corp", email="info@beta.com", company_id=company_id
    )
    session.add_all([customer1, customer2])
    session.commit()

    response = client.get("/customers?search=Acme")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "Acme Industries"


def test_search_customers_by_contact(client, session):
    """Test searching customers by contact person."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    customer = Customer(
        name="Test Corp",
        email="info@test.com",
        contact_person="John Doe",
        company_id=company_id,
    )
    session.add(customer)
    session.commit()

    response = client.get("/customers?search=John")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 1


##################################################
# Subcontractor Search Tests
##################################################
def test_search_subcontractors_by_name(client, session):
    """Test searching subcontractors by name."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    sub1 = Subcontractor(
        name="Tech Solutions", email="tech@sol.com", company_id=company_id
    )
    sub2 = Subcontractor(
        name="Build Corp", email="build@corp.com", company_id=company_id
    )
    session.add_all([sub1, sub2])
    session.commit()

    response = client.get("/subcontractors?search=Tech")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "Tech Solutions"


##################################################
# Combined Filters Tests
##################################################
def test_search_with_pagination(client, session):
    """Test search combined with pagination."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="TestUnit", company_id=company_id)
    session.add(unit)
    session.commit()

    # Create 5 developer positions
    for i in range(5):
        pos = Position(
            title=f"Developer {i}",
            company_id=company_id,
            organization_unit_id=unit.id,
        )
        session.add(pos)
    session.commit()

    # Search with pagination
    response = client.get("/positions?search=Developer&page=1&limit=2")
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["data"]) == 2
    assert result["pagination"]["total"] == 5
    assert result["pagination"]["pages"] == 3
