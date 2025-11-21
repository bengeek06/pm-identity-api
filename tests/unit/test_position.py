# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Test cases for the Position model and its associated endpoints.
"""

import uuid

from app.models.organization_unit import OrganizationUnit
from app.models.position import Position
from tests.unit.conftest import create_jwt_token


##################################################
# Test cases for GET /positions
##################################################
def test_get_positions_empty(client):
    """
    Test GET /positions when there are no positions.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    response = client.get("/positions")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_positions_single(client, session):
    """
    Test GET /positions with a single position.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="Unit1", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="Manager", company_id=company_id, organization_unit_id=unit.id
    )
    session.add(pos)
    session.commit()
    response = client.get("/positions")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["title"] == "Manager"
    assert item["company_id"] == company_id
    assert item["organization_unit_id"] == unit.id
    assert "id" in item


def test_get_positions_multiple(client, session):
    """
    Test GET /positions with multiple positions.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit1 = OrganizationUnit(name="UnitA", company_id="c1")
    unit2 = OrganizationUnit(name="UnitB", company_id="c2")
    session.add_all([unit1, unit2])
    session.commit()
    pos1 = Position(
        title="Dev", company_id="c1", organization_unit_id=unit1.id
    )
    pos2 = Position(
        title="Lead", company_id="c2", organization_unit_id=unit2.id
    )
    session.add_all([pos1, pos2])
    session.commit()
    response = client.get("/positions")
    assert response.status_code == 200
    data = response.get_json()
    titles = [item["title"] for item in data]
    assert "Dev" in titles
    assert "Lead" in titles
    ids = [item["organization_unit_id"] for item in data]
    assert unit1.id in ids
    assert unit2.id in ids


##################################################
# Test cases for POST /positions
##################################################
def test_post_position_success(client, session):
    """Test POST /positions with valid data."""
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitPost", company_id=company_id)
    session.add(unit)
    session.commit()
    payload = {
        "title": "Engineer",
        "organization_unit_id": unit.id,
    }
    response = client.post("/positions", json=payload)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["title"] == "Engineer"
    assert data["company_id"] == company_id
    assert data["organization_unit_id"] == unit.id
    assert "id" in data


def test_post_position_missing_title(client, session):
    """
    Test POST /positions with missing required 'title'.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitPost2", company_id=company_id)
    session.add(unit)
    session.commit()
    payload = {"organization_unit_id": unit.id}
    response = client.post("/positions", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "title" in str(data).lower()


def test_post_position_missing_organization_unit_id(client):
    """
    Test POST /positions with missing required 'organization_unit_id'.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"title": "NoUnit"}
    response = client.post("/positions", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "organization_unit_id" in str(data).lower()


def test_post_position_invalid_organization_unit_id(client):
    """
    Test POST /positions with invalid organization_unit_id (not found).
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {
        "title": "Ghost",
        "organization_unit_id": "not-a-real-id",
    }
    response = client.post("/positions", json=payload)
    assert response.status_code in (400, 404)


def test_post_position_duplicate_title(client, session):
    """
    Test POST /positions with duplicate title in the same unit if unique constraint exists.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitDup", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="UniqueTitle",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    session.add(pos)
    session.commit()
    payload = {
        "title": "UniqueTitle",
        "organization_unit_id": unit.id,
    }
    response = client.post("/positions", json=payload)
    # Si tu as une contrainte d'unicité, ce sera 400, sinon 201
    assert response.status_code in (201, 400)


##################################################
# Test cases for GET /positions/<id>
##################################################


def test_get_position_by_id_success(client, session):
    """
    Test GET /positions/<id> for an existing position.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitGet", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="Consultant", company_id=company_id, organization_unit_id=unit.id
    )
    session.add(pos)
    session.commit()

    response = client.get(f"/positions/{pos.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == pos.id
    assert data["title"] == "Consultant"
    assert data["company_id"] == company_id
    assert data["organization_unit_id"] == unit.id


def test_get_position_by_id_not_found(client):
    """
    Test GET /positions/<id> for a non-existent position.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    response = client.get(f"/positions/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data


##################################################
# Test cases for GET /organizationel_units/<id>/positions
##################################################


def test_get_positions_by_organization_unit_empty(client, session):
    """
    Test GET /organization_units/<id>/positions when the unit has no positions.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitNoPos", company_id=company_id)
    session.add(unit)
    session.commit()

    response = client.get(f"/organization_units/{unit.id}/positions")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_positions_by_organization_unit_with_positions(client, session):
    """
    Test GET /organization_units/<id>/positions when the unit has positions.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitWithPos", company_id=company_id)
    session.add(unit)
    session.commit()
    pos1 = Position(
        title="Dev", company_id=company_id, organization_unit_id=unit.id
    )
    pos2 = Position(
        title="Lead", company_id=company_id, organization_unit_id=unit.id
    )
    session.add_all([pos1, pos2])
    session.commit()

    response = client.get(f"/organization_units/{unit.id}/positions")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    titles = [item["title"] for item in data]
    assert "Dev" in titles
    assert "Lead" in titles
    for item in data:
        assert item["organization_unit_id"] == unit.id


def test_get_positions_by_organization_unit_not_found(client):
    """
    Test GET /organization_units/<id>/positions for a non-existent unit.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    response = client.get(f"/organization_units/{fake_id}/positions")
    # Selon l'implémentation, peut retourner 200 (liste vide) ou 404
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.get_json()
        assert isinstance(data, list)
    else:
        data = response.get_json()
        assert "error" in data or "message" in data


##################################################
# Test cases for POST /organizationel_units/<id>/positions
##################################################


def test_post_position_for_unit_success(client, session):
    """
    Test POST /organization_units/<id>/positions with valid data.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitForPost", company_id=company_id)
    session.add(unit)
    session.commit()
    payload = {
        "title": "Analyst",
        "organization_unit_id": unit.id,
    }
    response = client.post(
        f"/organization_units/{unit.id}/positions", json=payload
    )
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["title"] == "Analyst"
    assert data["company_id"] == company_id
    assert data["organization_unit_id"] == unit.id
    assert "id" in data


def test_post_position_for_unit_missing_title(client, session):
    """
    Test POST /organization_units/<id>/positions with missing required 'title'.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitForPost2", company_id=company_id)
    session.add(unit)
    session.commit()
    payload = {}
    response = client.post(
        f"/organization_units/{unit.id}/positions", json=payload
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "title" in str(data).lower()


def test_post_position_for_unit_invalid_unit_id(client):
    """
    Test POST /organization_units/<id>/positions with an invalid unit id.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    payload = {"title": "Ghost"}
    response = client.post(
        f"/organization_units/{fake_id}/positions", json=payload
    )
    assert response.status_code in (400, 404)
    data = response.get_json()
    assert (
        "organization_unit_id" in str(data).lower()
        or "error" in data
        or "message" in data
    )


def test_post_position_for_unit_duplicate_title(client, session):
    """
    Test POST /organization_units/<id>/positions with duplicate title.
    Checks if unique constraint exists in the same unit.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitForDup", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="UniqueAnalyst",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    session.add(pos)
    session.commit()
    payload = {"title": "UniqueAnalyst"}
    response = client.post(
        f"/organization_units/{unit.id}/positions", json=payload
    )
    # Si tu as une contrainte d'unicité, ce sera 400, sinon 201
    assert response.status_code in (201, 400)


##################################################
# Test cases for PUT /positions/<id>
##################################################
def test_put_position_success(client, session):
    """
    Test PUT /positions/<id> for a full update.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit1 = OrganizationUnit(name="UnitPut1", company_id=company_id)
    unit2 = OrganizationUnit(name="UnitPut2", company_id=company_id)
    session.add_all([unit1, unit2])
    session.commit()
    pos = Position(
        title="OldTitle", company_id=company_id, organization_unit_id=unit1.id
    )
    session.add(pos)
    session.commit()

    payload = {
        "title": "NewTitle",
        "organization_unit_id": unit2.id,
    }
    response = client.put(f"/positions/{pos.id}", json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["id"] == pos.id
    assert data["title"] == "NewTitle"
    assert data["company_id"] == company_id
    assert data["organization_unit_id"] == unit2.id


def test_put_position_not_found(client, session):
    """
    Test PUT /positions/<id> for a non-existent position.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitPutNF", company_id=company_id)
    session.add(unit)
    session.commit()
    fake_id = str(uuid.uuid4())
    payload = {
        "title": "DoesNotExist",
        "organization_unit_id": unit.id,
    }
    response = client.put(f"/positions/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data


def test_put_position_missing_title(client, session):
    """
    Test PUT /positions/<id> with missing required 'title'.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitPutMiss", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="ToBeUpdated",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    session.add(pos)
    session.commit()
    payload = {"organization_unit_id": unit.id}
    response = client.put(f"/positions/{pos.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "title" in str(data).lower()


def test_put_position_invalid_organization_unit_id(client, session):
    """
    Test PUT /positions/<id> with invalid organization_unit_id.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitPutInv", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="ToBeUpdated",
        company_id=company_id,
        organization_unit_id=unit.id,
    )
    session.add(pos)
    session.commit()
    payload = {
        "title": "StillHere",
        "organization_unit_id": "not-a-uuid",
    }
    response = client.put(f"/positions/{pos.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "organization_unit_id" in str(data).lower()


##################################################
# Test cases for PATCH /positions/<id>
##################################################
def test_patch_position_success(client, session):
    """
    Test PATCH /positions/<id> for a partial update (title only).
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitPatch", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="OldPatch", company_id=company_id, organization_unit_id=unit.id
    )
    session.add(pos)
    session.commit()

    payload = {"title": "NewPatch"}
    response = client.patch(f"/positions/{pos.id}", json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["id"] == pos.id
    assert data["title"] == "NewPatch"
    assert data["company_id"] == company_id
    assert data["organization_unit_id"] == unit.id


def test_patch_position_change_organization_unit(client, session):
    """
    Test PATCH /positions/<id> to change only the organization_unit_id.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit1 = OrganizationUnit(name="UnitPatch1", company_id=company_id)
    unit2 = OrganizationUnit(name="UnitPatch2", company_id=company_id)
    session.add_all([unit1, unit2])
    session.commit()
    pos = Position(
        title="PatchMove", company_id=company_id, organization_unit_id=unit1.id
    )
    session.add(pos)
    session.commit()

    payload = {"organization_unit_id": unit2.id}
    response = client.patch(f"/positions/{pos.id}", json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["organization_unit_id"] == unit2.id


def test_patch_position_not_found(client):
    """
    Test PATCH /positions/<id> for a non-existent position.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    payload = {"title": "NoPatch"}
    response = client.patch(f"/positions/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data


def test_patch_position_invalid_organization_unit_id(client, session):
    """
    Test PATCH /positions/<id> with invalid organization_unit_id.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitPatchInv", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="PatchInv", company_id=company_id, organization_unit_id=unit.id
    )
    session.add(pos)
    session.commit()
    payload = {"organization_unit_id": "not-a-uuid"}
    response = client.patch(f"/positions/{pos.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "organization_unit_id" in str(data).lower()


##################################################
# Test cases for DELETE /positions/<id>
##################################################
def test_delete_position_success(client, session):
    """
    Test DELETE /positions/<id> for an existing position.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    unit = OrganizationUnit(name="UnitDel", company_id=company_id)
    session.add(unit)
    session.commit()
    pos = Position(
        title="ToDelete", company_id=company_id, organization_unit_id=unit.id
    )
    session.add(pos)
    session.commit()

    response = client.delete(f"/positions/{pos.id}")
    assert response.status_code == 204

    # Vérifie que la position n'existe plus
    get_response = client.get(f"/positions/{pos.id}")
    assert get_response.status_code == 404


def test_delete_position_not_found(client):
    """
    Test DELETE /positions/<id> for a non-existent position.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    response = client.delete(f"/positions/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data
