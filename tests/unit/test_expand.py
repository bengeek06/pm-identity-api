# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Unit tests for the ?expand= query parameter functionality.

Tests cover:
- parse_expand utility function
- GET /users?expand=position list endpoint
- GET /users/{id}?expand=position single endpoint
- GET /positions?expand=organization_unit endpoint
- GET /organization_units?expand=positions,parent,children endpoint
"""

from typing import Any

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db
from app.models.company import Company
from app.models.organization_unit import OrganizationUnit
from app.models.position import Position
from app.models.user import User
from app.utils import parse_expand
from tests.unit.conftest import create_jwt_token

# Test password constant for fixtures (not a real credential)
TEST_PASSWORD = "Test@Fixture#9876"  # NOSONAR - test fixture password


# =============================================================================
# parse_expand utility function tests
# =============================================================================


class TestParseExpand:
    """Tests for the parse_expand utility function."""

    def test_parse_expand_none(self):
        """Test parse_expand with None input returns empty set."""
        result = parse_expand(None)
        assert result == set()

    def test_parse_expand_empty_string(self):
        """Test parse_expand with empty string returns empty set."""
        result = parse_expand("")
        assert result == set()

    def test_parse_expand_single_value(self):
        """Test parse_expand with single value."""
        result = parse_expand("position")
        assert result == {"position"}

    def test_parse_expand_multiple_values(self):
        """Test parse_expand with multiple comma-separated values."""
        result = parse_expand("position,organization")
        assert result == {"position", "organization"}

    def test_parse_expand_with_whitespace(self):
        """Test parse_expand handles whitespace correctly."""
        result = parse_expand("  position , organization  ")
        assert result == {"position", "organization"}

    def test_parse_expand_filters_unknown(self):
        """Test parse_expand filters unknown expansions when allowed set provided."""
        result = parse_expand("position,unknown,foo", {"position", "organization"})
        assert result == {"position"}

    def test_parse_expand_case_insensitive(self):
        """Test parse_expand normalizes to lowercase."""
        result = parse_expand("Position,ORGANIZATION", {"position", "organization"})
        assert result == {"position", "organization"}

    def test_parse_expand_duplicate_values(self):
        """Test parse_expand handles duplicate values."""
        result = parse_expand("position,position,position")
        assert result == {"position"}

    def test_parse_expand_empty_between_commas(self):
        """Test parse_expand handles empty values between commas."""
        result = parse_expand("position,,organization")
        assert result == {"position", "organization"}


# =============================================================================
# User expand endpoint tests
# =============================================================================


@pytest.fixture
def app_with_data():
    """Create app with test data including users with positions."""
    app = create_app("app.config.TestingConfig")
    with app.app_context():
        db.create_all()

        # Create company
        company = Company(name="Test Corp")  # type: ignore[call-arg]
        db.session.add(company)
        db.session.flush()

        # Create organization unit
        org_unit = OrganizationUnit(  # type: ignore[call-arg]
            name="Engineering",
            company_id=company.id,
            description="Engineering department",
        )
        db.session.add(org_unit)
        db.session.flush()

        # Create positions
        position1 = Position(  # type: ignore[call-arg]
            title="Software Engineer",
            description="Develops software",
            company_id=company.id,
            organization_unit_id=org_unit.id,
            level=3,
        )
        position2 = Position(  # type: ignore[call-arg]
            title="Tech Lead",
            description="Leads technical projects",
            company_id=company.id,
            organization_unit_id=org_unit.id,
            level=5,
        )
        db.session.add(position1)
        db.session.add(position2)
        db.session.flush()

        # Create users - one with position, one without
        user_with_position = User(  # type: ignore[call-arg]
            email="engineer@testcorp.com",
            hashed_password=generate_password_hash(TEST_PASSWORD),
            first_name="John",
            last_name="Doe",
            company_id=company.id,
            position_id=position1.id,
        )
        user_without_position = User(  # type: ignore[call-arg]
            email="new@testcorp.com",
            hashed_password=generate_password_hash(TEST_PASSWORD),
            first_name="Jane",
            last_name="Smith",
            company_id=company.id,
            position_id=None,
        )
        db.session.add(user_with_position)
        db.session.add(user_without_position)
        db.session.commit()

        # Store IDs for tests using a dict attached to app
        test_data: dict[str, Any] = {
            "company_id": company.id,
            "org_unit_id": org_unit.id,
            "position1_id": position1.id,
            "position2_id": position2.id,
            "user_with_position_id": user_with_position.id,
            "user_without_position_id": user_without_position.id,
        }
        setattr(app, "test_data", test_data)

        yield app

        db.session.remove()
        db.drop_all()


class TestUserListExpand:
    """Tests for GET /users with ?expand= parameter."""

    def test_get_users_without_expand(self, app_with_data):
        """Test GET /users without expand returns users without position object."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/users")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # Users should have position_id but NOT position object
            for user in data["data"]:
                assert "position_id" in user or user.get("position_id") is None
                assert "position" not in user

    def test_get_users_with_expand_position(self, app_with_data):
        """Test GET /users?expand=position includes position objects."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/users?expand=position")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data
            assert len(data["data"]) >= 1

            # Find user with position
            user_with_pos = next(
                (u for u in data["data"] if u["id"] == app_with_data.test_data["user_with_position_id"]),
                None,
            )
            assert user_with_pos is not None
            assert "position" in user_with_pos
            assert user_with_pos["position"] is not None
            assert user_with_pos["position"]["title"] == "Software Engineer"
            assert user_with_pos["position"]["description"] == "Develops software"
            assert user_with_pos["position"]["level"] == 3

            # Find user without position
            user_without_pos = next(
                (u for u in data["data"] if u["id"] == app_with_data.test_data["user_without_position_id"]),
                None,
            )
            assert user_without_pos is not None
            assert "position" in user_without_pos
            assert user_without_pos["position"] is None

    def test_get_users_with_unknown_expand(self, app_with_data):
        """Test GET /users?expand=unknown silently ignores unknown expansions."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/users?expand=unknown,foo,bar")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # No expansion should be added
            for user in data["data"]:
                assert "position" not in user

    def test_get_users_with_mixed_expand(self, app_with_data):
        """Test GET /users?expand=position,unknown only expands valid relations."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/users?expand=position,unknown")

            assert response.status_code == 200
            data = response.get_json()

            # Position should be expanded
            user_with_pos = next(
                (u for u in data["data"] if u["id"] == app_with_data.test_data["user_with_position_id"]),
                None,
            )
            assert user_with_pos is not None
            assert "position" in user_with_pos
            assert user_with_pos["position"]["title"] == "Software Engineer"

    def test_get_users_with_empty_expand(self, app_with_data):
        """Test GET /users?expand= with empty value returns normal response."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/users?expand=")

            assert response.status_code == 200
            data = response.get_json()

            # No expansion
            for user in data["data"]:
                assert "position" not in user


class TestUserSingleExpand:
    """Tests for GET /users/{id} with ?expand= parameter."""

    def test_get_user_without_expand(self, app_with_data):
        """Test GET /users/{id} without expand returns user without position object."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            user_id = app_with_data.test_data["user_with_position_id"]
            response = client.get(f"/users/{user_id}")

            assert response.status_code == 200
            data = response.get_json()

            # Should have position_id but NOT position object
            assert "position_id" in data
            assert "position" not in data

    def test_get_user_with_expand_position(self, app_with_data):
        """Test GET /users/{id}?expand=position includes position object."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            user_id = app_with_data.test_data["user_with_position_id"]
            response = client.get(f"/users/{user_id}?expand=position")

            assert response.status_code == 200
            data = response.get_json()

            # Should have both position_id and position object
            assert "position_id" in data
            assert "position" in data
            assert data["position"] is not None
            assert data["position"]["title"] == "Software Engineer"
            assert data["position"]["description"] == "Develops software"
            assert data["position"]["level"] == 3
            assert "organization_unit_id" in data["position"]

    def test_get_user_without_position_expand(self, app_with_data):
        """Test GET /users/{id}?expand=position for user without position."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_without_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            user_id = app_with_data.test_data["user_without_position_id"]
            response = client.get(f"/users/{user_id}?expand=position")

            assert response.status_code == 200
            data = response.get_json()

            # Should have position key but value is None
            assert "position" in data
            assert data["position"] is None

    def test_get_user_not_found_with_expand(self, app_with_data):
        """Test GET /users/{id}?expand=position returns 404 for non-existent user."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/users/00000000-0000-0000-0000-000000000000?expand=position")

            assert response.status_code == 404

    def test_get_user_with_unknown_expand(self, app_with_data):
        """Test GET /users/{id}?expand=unknown silently ignores unknown expansions."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            user_id = app_with_data.test_data["user_with_position_id"]
            response = client.get(f"/users/{user_id}?expand=unknown")

            assert response.status_code == 200
            data = response.get_json()

            # No expansion
            assert "position" not in data


class TestExpandPositionSchema:
    """Tests for the PositionNestedSchema structure."""

    def test_position_schema_fields(self, app_with_data):
        """Test that expanded position includes expected fields."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            user_id = app_with_data.test_data["user_with_position_id"]
            response = client.get(f"/users/{user_id}?expand=position")

            assert response.status_code == 200
            data = response.get_json()
            position = data["position"]

            # Verify expected fields are present
            assert "id" in position
            assert "title" in position
            assert "description" in position
            assert "level" in position
            assert "organization_unit_id" in position

            # Verify no sensitive or unnecessary fields
            assert "company_id" not in position  # Not exposed in nested schema
            assert "created_at" not in position
            assert "updated_at" not in position


# =============================================================================
# Position expand endpoint tests
# =============================================================================


class TestPositionListExpand:
    """Tests for GET /positions with ?expand= parameter."""

    def test_get_positions_without_expand(self, app_with_data):
        """Test GET /positions without expand returns positions without organization_unit object."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/positions")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # Positions should have organization_unit_id but NOT organization_unit object
            for position in data["data"]:
                assert "organization_unit_id" in position
                assert "organization_unit" not in position

    def test_get_positions_with_expand_organization_unit(self, app_with_data):
        """Test GET /positions?expand=organization_unit includes organization_unit objects."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/positions?expand=organization_unit")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data
            assert len(data["data"]) >= 1

            # All positions should have organization_unit expanded
            for position in data["data"]:
                assert "organization_unit" in position
                assert position["organization_unit"] is not None
                assert position["organization_unit"]["name"] == "Engineering"
                assert "id" in position["organization_unit"]
                assert "description" in position["organization_unit"]
                assert "level" in position["organization_unit"]
                assert "parent_id" in position["organization_unit"]
                assert "path" in position["organization_unit"]

    def test_get_positions_with_unknown_expand(self, app_with_data):
        """Test GET /positions?expand=unknown silently ignores unknown expansions."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/positions?expand=unknown,foo")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # No expansion should be added
            for position in data["data"]:
                assert "organization_unit" not in position


class TestPositionSingleExpand:
    """Tests for GET /positions/{id} with ?expand= parameter."""

    def test_get_position_without_expand(self, app_with_data):
        """Test GET /positions/{id} without expand returns position without organization_unit object."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            position_id = app_with_data.test_data["position1_id"]
            response = client.get(f"/positions/{position_id}")

            assert response.status_code == 200
            data = response.get_json()

            # Should have organization_unit_id but NOT organization_unit object
            assert "organization_unit_id" in data
            assert "organization_unit" not in data

    def test_get_position_with_expand_organization_unit(self, app_with_data):
        """Test GET /positions/{id}?expand=organization_unit includes organization_unit object."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            position_id = app_with_data.test_data["position1_id"]
            response = client.get(f"/positions/{position_id}?expand=organization_unit")

            assert response.status_code == 200
            data = response.get_json()

            # Should have both organization_unit_id and organization_unit object
            assert "organization_unit_id" in data
            assert "organization_unit" in data
            assert data["organization_unit"] is not None
            assert data["organization_unit"]["name"] == "Engineering"
            assert "id" in data["organization_unit"]
            assert "level" in data["organization_unit"]
            assert "parent_id" in data["organization_unit"]

    def test_get_position_not_found_with_expand(self, app_with_data):
        """Test GET /positions/{id}?expand=organization_unit returns 404 for non-existent position."""
        with app_with_data.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_data.test_data["user_with_position_id"],
                company_id=app_with_data.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get(
                "/positions/00000000-0000-0000-0000-000000000000?expand=organization_unit"
            )

            assert response.status_code == 404


# =============================================================================
# OrganizationUnit expand endpoint tests
# =============================================================================


@pytest.fixture
def app_with_hierarchy():
    """Create app with test data including organization unit hierarchy."""
    app = create_app("app.config.TestingConfig")
    with app.app_context():
        db.create_all()

        # Create company
        company = Company(name="Hierarchy Corp")  # type: ignore[call-arg]
        db.session.add(company)
        db.session.flush()

        # Create organization unit hierarchy
        # Root unit (no parent)
        root_unit = OrganizationUnit(  # type: ignore[call-arg]
            name="Root Department",
            company_id=company.id,
            description="Root organization unit",
        )
        db.session.add(root_unit)
        db.session.flush()
        root_unit.update_path_and_level()

        # Child unit 1
        child_unit1 = OrganizationUnit(  # type: ignore[call-arg]
            name="Child Department 1",
            company_id=company.id,
            description="First child unit",
            parent_id=root_unit.id,
        )
        db.session.add(child_unit1)
        db.session.flush()
        child_unit1.update_path_and_level()

        # Child unit 2
        child_unit2 = OrganizationUnit(  # type: ignore[call-arg]
            name="Child Department 2",
            company_id=company.id,
            description="Second child unit",
            parent_id=root_unit.id,
        )
        db.session.add(child_unit2)
        db.session.flush()
        child_unit2.update_path_and_level()

        # Grandchild unit (child of child1)
        grandchild_unit = OrganizationUnit(  # type: ignore[call-arg]
            name="Grandchild Department",
            company_id=company.id,
            description="Grandchild unit",
            parent_id=child_unit1.id,
        )
        db.session.add(grandchild_unit)
        db.session.flush()
        grandchild_unit.update_path_and_level()

        # Create positions for root unit
        position1 = Position(  # type: ignore[call-arg]
            title="Director",
            description="Department director",
            company_id=company.id,
            organization_unit_id=root_unit.id,
            level=5,
        )
        position2 = Position(  # type: ignore[call-arg]
            title="Manager",
            description="Department manager",
            company_id=company.id,
            organization_unit_id=root_unit.id,
            level=4,
        )
        db.session.add(position1)
        db.session.add(position2)
        db.session.flush()

        # Create user for authentication
        user = User(  # type: ignore[call-arg]
            email="admin@hierarchy.com",
            hashed_password=generate_password_hash(TEST_PASSWORD),
            first_name="Admin",
            last_name="User",
            company_id=company.id,
        )
        db.session.add(user)
        db.session.commit()

        # Store IDs for tests using setattr to avoid Pylance errors
        test_data: dict[str, Any] = {
            "company_id": company.id,
            "root_unit_id": root_unit.id,
            "child_unit1_id": child_unit1.id,
            "child_unit2_id": child_unit2.id,
            "grandchild_unit_id": grandchild_unit.id,
            "position1_id": position1.id,
            "position2_id": position2.id,
            "user_id": user.id,
        }
        setattr(app, "test_data", test_data)

        yield app

        db.session.remove()
        db.drop_all()


class TestOrganizationUnitListExpand:
    """Tests for GET /organization_units with ?expand= parameter."""

    def test_get_org_units_without_expand(self, app_with_hierarchy):
        """Test GET /organization_units without expand returns units without expanded relations."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/organization_units")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # Units should NOT have expanded relations
            for unit in data["data"]:
                assert "positions" not in unit
                assert "parent" not in unit
                assert "children" not in unit

    def test_get_org_units_with_expand_positions(self, app_with_hierarchy):
        """Test GET /organization_units?expand=positions includes positions."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/organization_units?expand=positions")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # Find root unit which has positions
            root_unit = next(
                (u for u in data["data"] if u["id"] == app_with_hierarchy.test_data["root_unit_id"]),
                None,
            )
            assert root_unit is not None
            assert "positions" in root_unit
            assert len(root_unit["positions"]) == 2
            assert root_unit["positions"][0]["title"] in ["Director", "Manager"]

    def test_get_org_units_with_expand_parent(self, app_with_hierarchy):
        """Test GET /organization_units?expand=parent includes parent."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/organization_units?expand=parent")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # Find child unit which has a parent
            child_unit = next(
                (u for u in data["data"] if u["id"] == app_with_hierarchy.test_data["child_unit1_id"]),
                None,
            )
            assert child_unit is not None
            assert "parent" in child_unit
            assert child_unit["parent"] is not None
            assert child_unit["parent"]["name"] == "Root Department"

            # Find root unit which has no parent
            root_unit = next(
                (u for u in data["data"] if u["id"] == app_with_hierarchy.test_data["root_unit_id"]),
                None,
            )
            assert root_unit is not None
            assert "parent" in root_unit
            assert root_unit["parent"] is None

    def test_get_org_units_with_expand_children(self, app_with_hierarchy):
        """Test GET /organization_units?expand=children includes children."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/organization_units?expand=children")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # Find root unit which has children
            root_unit = next(
                (u for u in data["data"] if u["id"] == app_with_hierarchy.test_data["root_unit_id"]),
                None,
            )
            assert root_unit is not None
            assert "children" in root_unit
            assert len(root_unit["children"]) == 2
            child_names = {c["name"] for c in root_unit["children"]}
            assert child_names == {"Child Department 1", "Child Department 2"}

    def test_get_org_units_with_multiple_expand(self, app_with_hierarchy):
        """Test GET /organization_units?expand=positions,parent,children includes all."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get("/organization_units?expand=positions,parent,children")

            assert response.status_code == 200
            data = response.get_json()
            assert "data" in data

            # All units should have all three expansions
            for unit in data["data"]:
                assert "positions" in unit
                assert "parent" in unit
                assert "children" in unit


class TestOrganizationUnitSingleExpand:
    """Tests for GET /organization_units/{id} with ?expand= parameter."""

    def test_get_org_unit_without_expand(self, app_with_hierarchy):
        """Test GET /organization_units/{id} without expand returns unit without expanded relations."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            unit_id = app_with_hierarchy.test_data["root_unit_id"]
            response = client.get(f"/organization_units/{unit_id}")

            assert response.status_code == 200
            data = response.get_json()

            # Should NOT have expanded relations
            assert "positions" not in data
            assert "parent" not in data
            assert "children" not in data

    def test_get_org_unit_with_expand_positions(self, app_with_hierarchy):
        """Test GET /organization_units/{id}?expand=positions includes positions."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            unit_id = app_with_hierarchy.test_data["root_unit_id"]
            response = client.get(f"/organization_units/{unit_id}?expand=positions")

            assert response.status_code == 200
            data = response.get_json()

            assert "positions" in data
            assert len(data["positions"]) == 2
            position_titles = {p["title"] for p in data["positions"]}
            assert position_titles == {"Director", "Manager"}

    def test_get_org_unit_with_expand_parent(self, app_with_hierarchy):
        """Test GET /organization_units/{id}?expand=parent includes parent."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            # Test child unit with parent
            unit_id = app_with_hierarchy.test_data["child_unit1_id"]
            response = client.get(f"/organization_units/{unit_id}?expand=parent")

            assert response.status_code == 200
            data = response.get_json()

            assert "parent" in data
            assert data["parent"] is not None
            assert data["parent"]["name"] == "Root Department"
            assert "id" in data["parent"]
            assert "level" in data["parent"]

    def test_get_org_unit_with_expand_children(self, app_with_hierarchy):
        """Test GET /organization_units/{id}?expand=children includes children."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            unit_id = app_with_hierarchy.test_data["root_unit_id"]
            response = client.get(f"/organization_units/{unit_id}?expand=children")

            assert response.status_code == 200
            data = response.get_json()

            assert "children" in data
            assert len(data["children"]) == 2
            child_names = {c["name"] for c in data["children"]}
            assert child_names == {"Child Department 1", "Child Department 2"}

    def test_get_org_unit_with_all_expansions(self, app_with_hierarchy):
        """Test GET /organization_units/{id}?expand=positions,parent,children includes all."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            # Test child unit 1 which has parent, children (grandchild), and potentially positions
            unit_id = app_with_hierarchy.test_data["child_unit1_id"]
            response = client.get(f"/organization_units/{unit_id}?expand=positions,parent,children")

            assert response.status_code == 200
            data = response.get_json()

            assert "positions" in data
            assert "parent" in data
            assert "children" in data
            assert data["parent"]["name"] == "Root Department"
            assert len(data["children"]) == 1  # grandchild
            assert data["children"][0]["name"] == "Grandchild Department"

    def test_get_org_unit_not_found_with_expand(self, app_with_hierarchy):
        """Test GET /organization_units/{id}?expand=positions returns 404 for non-existent unit."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            response = client.get(
                "/organization_units/00000000-0000-0000-0000-000000000000?expand=positions"
            )

            assert response.status_code == 404

    def test_get_org_unit_with_unknown_expand(self, app_with_hierarchy):
        """Test GET /organization_units/{id}?expand=unknown silently ignores unknown expansions."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            unit_id = app_with_hierarchy.test_data["root_unit_id"]
            response = client.get(f"/organization_units/{unit_id}?expand=unknown,foo")

            assert response.status_code == 200
            data = response.get_json()

            # No expansions should be added
            assert "positions" not in data
            assert "parent" not in data
            assert "children" not in data


class TestExpandOrganizationUnitNestedSchema:
    """Tests for the OrganizationUnitNestedSchema structure."""

    def test_org_unit_nested_schema_fields(self, app_with_hierarchy):
        """Test that expanded organization_unit includes expected fields."""
        with app_with_hierarchy.test_client() as client:
            token = create_jwt_token(
                user_id=app_with_hierarchy.test_data["user_id"],
                company_id=app_with_hierarchy.test_data["company_id"],
            )
            client.set_cookie("access_token", token)

            unit_id = app_with_hierarchy.test_data["child_unit1_id"]
            response = client.get(f"/organization_units/{unit_id}?expand=parent")

            assert response.status_code == 200
            data = response.get_json()
            parent = data["parent"]

            # Verify expected fields are present
            assert "id" in parent
            assert "name" in parent
            assert "description" in parent
            assert "level" in parent
            assert "parent_id" in parent
            assert "path" in parent

            # Verify no sensitive or unnecessary fields
            assert "company_id" not in parent
            assert "created_at" not in parent
            assert "updated_at" not in parent
