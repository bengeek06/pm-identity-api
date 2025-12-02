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
"""

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
        company = Company(name="Test Corp")
        db.session.add(company)
        db.session.flush()

        # Create organization unit
        org_unit = OrganizationUnit(
            name="Engineering",
            company_id=company.id,
            description="Engineering department",
        )
        db.session.add(org_unit)
        db.session.flush()

        # Create positions
        position1 = Position(
            title="Software Engineer",
            description="Develops software",
            company_id=company.id,
            organization_unit_id=org_unit.id,
            level=3,
        )
        position2 = Position(
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
        user_with_position = User(
            email="engineer@testcorp.com",
            hashed_password=generate_password_hash("password123"),
            first_name="John",
            last_name="Doe",
            company_id=company.id,
            position_id=position1.id,
        )
        user_without_position = User(
            email="new@testcorp.com",
            hashed_password=generate_password_hash("password123"),
            first_name="Jane",
            last_name="Smith",
            company_id=company.id,
            position_id=None,
        )
        db.session.add(user_with_position)
        db.session.add(user_without_position)
        db.session.commit()

        # Store IDs for tests
        app.test_data = {
            "company_id": company.id,
            "org_unit_id": org_unit.id,
            "position1_id": position1.id,
            "position2_id": position2.id,
            "user_with_position_id": user_with_position.id,
            "user_without_position_id": user_without_position.id,
        }

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
