# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Test cases for the id__in query parameter filter on list endpoints.

Issue #70: Add id__in filter support for:
- GET /users
- GET /companies
- GET /customers
- GET /subcontractors
- GET /positions
- GET /organization_units

Tests cover:
1. Normal case: filtering by existing IDs
2. Empty string case: returns empty list with 200
3. Non-existent IDs: returns empty list (silent filtering)
4. Mixed existing/non-existent IDs: returns only matching records
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
# Test cases for GET /users?id__in
##################################################
class TestUserIdInFilter:
    """Tests for id__in filter on /users endpoint."""

    def test_get_users_id_in_single_id(self, client, session):
        """Test GET /users?id__in with a single matching ID."""
        company_id = str(uuid.uuid4())
        user1 = User(
            email="user1@example.com",
            hashed_password="hashedpw1",
            first_name="Alice",
            last_name="Smith",
            company_id=company_id,
        )
        user2 = User(
            email="user2@example.com",
            hashed_password="hashedpw2",
            first_name="Bob",
            last_name="Jones",
            company_id=company_id,
        )
        session.add_all([user1, user2])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(user1.id))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/users?id__in={user1.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == str(user1.id)
        assert result["pagination"]["total"] == 1

    def test_get_users_id_in_multiple_ids(self, client, session):
        """Test GET /users?id__in with multiple matching IDs."""
        company_id = str(uuid.uuid4())
        user1 = User(
            email="user1@example.com",
            hashed_password="hashedpw1",
            first_name="Alice",
            last_name="Smith",
            company_id=company_id,
        )
        user2 = User(
            email="user2@example.com",
            hashed_password="hashedpw2",
            first_name="Bob",
            last_name="Jones",
            company_id=company_id,
        )
        user3 = User(
            email="user3@example.com",
            hashed_password="hashedpw3",
            first_name="Carol",
            last_name="Brown",
            company_id=company_id,
        )
        session.add_all([user1, user2, user3])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(user1.id))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/users?id__in={user1.id},{user2.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 2
        ids = [u["id"] for u in result["data"]]
        assert str(user1.id) in ids
        assert str(user2.id) in ids
        assert result["pagination"]["total"] == 2

    def test_get_users_id_in_empty_string(self, client, session):
        """Test GET /users?id__in= (empty string) returns empty list."""
        company_id = str(uuid.uuid4())
        user = User(
            email="user@example.com",
            hashed_password="hashedpw",
            first_name="Alice",
            last_name="Smith",
            company_id=company_id,
        )
        session.add(user)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(user.id))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get("/users?id__in=")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_get_users_id_in_nonexistent_ids(self, client, session):
        """Test GET /users?id__in with non-existent IDs returns empty list."""
        company_id = str(uuid.uuid4())
        user = User(
            email="user@example.com",
            hashed_password="hashedpw",
            first_name="Alice",
            last_name="Smith",
            company_id=company_id,
        )
        session.add(user)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(user.id))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        fake_id = str(uuid.uuid4())
        response = client.get(f"/users?id__in={fake_id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_get_users_id_in_mixed_ids(self, client, session):
        """Test GET /users?id__in with mix of existing and non-existent IDs."""
        company_id = str(uuid.uuid4())
        user = User(
            email="user@example.com",
            hashed_password="hashedpw",
            first_name="Alice",
            last_name="Smith",
            company_id=company_id,
        )
        session.add(user)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(user.id))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        fake_id = str(uuid.uuid4())
        response = client.get(f"/users?id__in={user.id},{fake_id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == str(user.id)
        assert result["pagination"]["total"] == 1


##################################################
# Test cases for GET /companies?id__in
##################################################
class TestCompanyIdInFilter:
    """Tests for id__in filter on /companies endpoint."""

    def test_get_companies_id_in_single_id(self, client, session):
        """Test GET /companies?id__in with a single matching ID."""
        company1 = Company(name="Company A")
        company2 = Company(name="Company B")
        session.add_all([company1, company2])
        session.commit()

        jwt_token = create_jwt_token(str(company1.id), str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/companies?id__in={company1.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == str(company1.id)
        assert result["pagination"]["total"] == 1

    def test_get_companies_id_in_multiple_ids(self, client, session):
        """Test GET /companies?id__in with multiple matching IDs."""
        company1 = Company(name="Company A")
        company2 = Company(name="Company B")
        company3 = Company(name="Company C")
        session.add_all([company1, company2, company3])
        session.commit()

        jwt_token = create_jwt_token(str(company1.id), str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/companies?id__in={company1.id},{company2.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 2
        ids = [c["id"] for c in result["data"]]
        assert str(company1.id) in ids
        assert str(company2.id) in ids
        assert result["pagination"]["total"] == 2

    def test_get_companies_id_in_empty_string(self, client, session):
        """Test GET /companies?id__in= (empty string) returns empty list."""
        company = Company(name="Company A")
        session.add(company)
        session.commit()

        jwt_token = create_jwt_token(str(company.id), str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get("/companies?id__in=")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_get_companies_id_in_nonexistent_ids(self, client, session):
        """Test GET /companies?id__in with non-existent IDs returns empty list."""
        company = Company(name="Company A")
        session.add(company)
        session.commit()

        jwt_token = create_jwt_token(str(company.id), str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        fake_id = str(uuid.uuid4())
        response = client.get(f"/companies?id__in={fake_id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0


##################################################
# Test cases for GET /customers?id__in
##################################################
class TestCustomerIdInFilter:
    """Tests for id__in filter on /customers endpoint."""

    def test_get_customers_id_in_single_id(self, client, session):
        """Test GET /customers?id__in with a single matching ID."""
        company_id = str(uuid.uuid4())
        customer1 = Customer(name="Customer A", company_id=company_id)
        customer2 = Customer(name="Customer B", company_id=company_id)
        session.add_all([customer1, customer2])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/customers?id__in={customer1.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == str(customer1.id)
        assert result["pagination"]["total"] == 1

    def test_get_customers_id_in_multiple_ids(self, client, session):
        """Test GET /customers?id__in with multiple matching IDs."""
        company_id = str(uuid.uuid4())
        customer1 = Customer(name="Customer A", company_id=company_id)
        customer2 = Customer(name="Customer B", company_id=company_id)
        customer3 = Customer(name="Customer C", company_id=company_id)
        session.add_all([customer1, customer2, customer3])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(
            f"/customers?id__in={customer1.id},{customer2.id}"
        )
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 2
        ids = [c["id"] for c in result["data"]]
        assert str(customer1.id) in ids
        assert str(customer2.id) in ids
        assert result["pagination"]["total"] == 2

    def test_get_customers_id_in_empty_string(self, client, session):
        """Test GET /customers?id__in= (empty string) returns empty list."""
        company_id = str(uuid.uuid4())
        customer = Customer(name="Customer A", company_id=company_id)
        session.add(customer)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get("/customers?id__in=")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_get_customers_id_in_nonexistent_ids(self, client, session):
        """Test GET /customers?id__in with non-existent IDs returns empty list."""
        company_id = str(uuid.uuid4())
        customer = Customer(name="Customer A", company_id=company_id)
        session.add(customer)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        fake_id = str(uuid.uuid4())
        response = client.get(f"/customers?id__in={fake_id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0


##################################################
# Test cases for GET /subcontractors?id__in
##################################################
class TestSubcontractorIdInFilter:
    """Tests for id__in filter on /subcontractors endpoint."""

    def test_get_subcontractors_id_in_single_id(self, client, session):
        """Test GET /subcontractors?id__in with a single matching ID."""
        company_id = str(uuid.uuid4())
        subcontractor1 = Subcontractor(name="Sub A", company_id=company_id)
        subcontractor2 = Subcontractor(name="Sub B", company_id=company_id)
        session.add_all([subcontractor1, subcontractor2])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/subcontractors?id__in={subcontractor1.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == str(subcontractor1.id)
        assert result["pagination"]["total"] == 1

    def test_get_subcontractors_id_in_multiple_ids(self, client, session):
        """Test GET /subcontractors?id__in with multiple matching IDs."""
        company_id = str(uuid.uuid4())
        subcontractor1 = Subcontractor(name="Sub A", company_id=company_id)
        subcontractor2 = Subcontractor(name="Sub B", company_id=company_id)
        subcontractor3 = Subcontractor(name="Sub C", company_id=company_id)
        session.add_all([subcontractor1, subcontractor2, subcontractor3])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(
            f"/subcontractors?id__in={subcontractor1.id},{subcontractor2.id}"
        )
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 2
        ids = [s["id"] for s in result["data"]]
        assert str(subcontractor1.id) in ids
        assert str(subcontractor2.id) in ids
        assert result["pagination"]["total"] == 2

    def test_get_subcontractors_id_in_empty_string(self, client, session):
        """Test GET /subcontractors?id__in= (empty string) returns empty list."""
        company_id = str(uuid.uuid4())
        subcontractor = Subcontractor(name="Sub A", company_id=company_id)
        session.add(subcontractor)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get("/subcontractors?id__in=")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_get_subcontractors_id_in_nonexistent_ids(self, client, session):
        """Test GET /subcontractors?id__in with non-existent IDs returns empty list."""
        company_id = str(uuid.uuid4())
        subcontractor = Subcontractor(name="Sub A", company_id=company_id)
        session.add(subcontractor)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        fake_id = str(uuid.uuid4())
        response = client.get(f"/subcontractors?id__in={fake_id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0


##################################################
# Test cases for GET /positions?id__in
##################################################
class TestPositionIdInFilter:
    """Tests for id__in filter on /positions endpoint."""

    def test_get_positions_id_in_single_id(self, client, session):
        """Test GET /positions?id__in with a single matching ID."""
        company_id = str(uuid.uuid4())
        org_unit = OrganizationUnit(name="Dept A", company_id=company_id)
        session.add(org_unit)
        session.flush()

        position1 = Position(
            title="Position A",
            company_id=company_id,
            organization_unit_id=org_unit.id,
        )
        position2 = Position(
            title="Position B",
            company_id=company_id,
            organization_unit_id=org_unit.id,
        )
        session.add_all([position1, position2])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/positions?id__in={position1.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == str(position1.id)
        assert result["pagination"]["total"] == 1

    def test_get_positions_id_in_multiple_ids(self, client, session):
        """Test GET /positions?id__in with multiple matching IDs."""
        company_id = str(uuid.uuid4())
        org_unit = OrganizationUnit(name="Dept A", company_id=company_id)
        session.add(org_unit)
        session.flush()

        position1 = Position(
            title="Position A",
            company_id=company_id,
            organization_unit_id=org_unit.id,
        )
        position2 = Position(
            title="Position B",
            company_id=company_id,
            organization_unit_id=org_unit.id,
        )
        position3 = Position(
            title="Position C",
            company_id=company_id,
            organization_unit_id=org_unit.id,
        )
        session.add_all([position1, position2, position3])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(
            f"/positions?id__in={position1.id},{position2.id}"
        )
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 2
        ids = [p["id"] for p in result["data"]]
        assert str(position1.id) in ids
        assert str(position2.id) in ids
        assert result["pagination"]["total"] == 2

    def test_get_positions_id_in_empty_string(self, client, session):
        """Test GET /positions?id__in= (empty string) returns empty list."""
        company_id = str(uuid.uuid4())
        org_unit = OrganizationUnit(name="Dept A", company_id=company_id)
        session.add(org_unit)
        session.flush()

        position = Position(
            title="Position A",
            company_id=company_id,
            organization_unit_id=org_unit.id,
        )
        session.add(position)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get("/positions?id__in=")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_get_positions_id_in_nonexistent_ids(self, client, session):
        """Test GET /positions?id__in with non-existent IDs returns empty list."""
        company_id = str(uuid.uuid4())
        org_unit = OrganizationUnit(name="Dept A", company_id=company_id)
        session.add(org_unit)
        session.flush()

        position = Position(
            title="Position A",
            company_id=company_id,
            organization_unit_id=org_unit.id,
        )
        session.add(position)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        fake_id = str(uuid.uuid4())
        response = client.get(f"/positions?id__in={fake_id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0


##################################################
# Test cases for GET /organization_units?id__in
##################################################
class TestOrganizationUnitIdInFilter:
    """Tests for id__in filter on /organization_units endpoint."""

    def test_get_org_units_id_in_single_id(self, client, session):
        """Test GET /organization_units?id__in with a single matching ID."""
        company_id = str(uuid.uuid4())
        org_unit1 = OrganizationUnit(name="Dept A", company_id=company_id)
        org_unit2 = OrganizationUnit(name="Dept B", company_id=company_id)
        session.add_all([org_unit1, org_unit2])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(f"/organization_units?id__in={org_unit1.id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == str(org_unit1.id)
        assert result["pagination"]["total"] == 1

    def test_get_org_units_id_in_multiple_ids(self, client, session):
        """Test GET /organization_units?id__in with multiple matching IDs."""
        company_id = str(uuid.uuid4())
        org_unit1 = OrganizationUnit(name="Dept A", company_id=company_id)
        org_unit2 = OrganizationUnit(name="Dept B", company_id=company_id)
        org_unit3 = OrganizationUnit(name="Dept C", company_id=company_id)
        session.add_all([org_unit1, org_unit2, org_unit3])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get(
            f"/organization_units?id__in={org_unit1.id},{org_unit2.id}"
        )
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 2
        ids = [o["id"] for o in result["data"]]
        assert str(org_unit1.id) in ids
        assert str(org_unit2.id) in ids
        assert result["pagination"]["total"] == 2

    def test_get_org_units_id_in_empty_string(self, client, session):
        """Test GET /organization_units?id__in= (empty string) returns empty list."""
        company_id = str(uuid.uuid4())
        org_unit = OrganizationUnit(name="Dept A", company_id=company_id)
        session.add(org_unit)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get("/organization_units?id__in=")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_get_org_units_id_in_nonexistent_ids(self, client, session):
        """Test GET /organization_units?id__in with non-existent IDs returns empty list."""
        company_id = str(uuid.uuid4())
        org_unit = OrganizationUnit(name="Dept A", company_id=company_id)
        session.add(org_unit)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        fake_id = str(uuid.uuid4())
        response = client.get(f"/organization_units?id__in={fake_id}")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0


##################################################
# Additional edge case tests
##################################################
class TestIdInFilterEdgeCases:
    """Tests for edge cases in id__in filter."""

    def test_id_in_with_whitespace(self, client, session):
        """Test id__in filter handles whitespace in IDs."""
        company_id = str(uuid.uuid4())
        company1 = Company(name="Company A")
        company2 = Company(name="Company B")
        session.add_all([company1, company2])
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        # Test with spaces around IDs
        response = client.get(
            f"/companies?id__in= {company1.id} , {company2.id} "
        )
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 2

    def test_id_in_only_whitespace(self, client, session):
        """Test id__in filter with only whitespace returns empty list."""
        company_id = str(uuid.uuid4())
        company = Company(name="Company A")
        session.add(company)
        session.commit()

        jwt_token = create_jwt_token(company_id, str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        response = client.get("/companies?id__in=   ")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0

    def test_id_in_combined_with_other_filters(self, client, session):
        """Test id__in filter can be combined with other filters."""
        company1 = Company(name="ACME Corp")
        company2 = Company(name="ACME Inc")
        company3 = Company(name="Other Company")
        session.add_all([company1, company2, company3])
        session.commit()

        jwt_token = create_jwt_token(str(company1.id), str(uuid.uuid4()))
        client.set_cookie("access_token", jwt_token, domain="localhost")

        # Combine id__in with search filter
        response = client.get(
            f"/companies?id__in={company1.id},{company2.id},{company3.id}&search=ACME"
        )
        assert response.status_code == 200
        result = response.get_json()
        # Should only return companies that match both filters
        assert len(result["data"]) == 2
        names = [c["name"] for c in result["data"]]
        assert "ACME Corp" in names
        assert "ACME Inc" in names
