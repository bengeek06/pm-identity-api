"""Test the creation of a new organization unit."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.organization_unit import OrganizationUnit
from tests.conftest import create_jwt_token


##################################################
# Test cases for GET /organization_units
##################################################
def test_get_organization_units_empty(client, session):
    """
    Test GET /organization_units when there are no organization units.
    Should return an empty list.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Assure-toi que la table est vide
    session.query(OrganizationUnit).delete()
    session.commit()
    response = client.get("/organization_units")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_organization_units_single(client, session):
    """
    Test GET /organization_units with a single organization unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="Root", company_id="c1")
    session.add(org)
    session.commit()
    response = client.get("/organization_units")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["name"] == "Root"
    assert item["company_id"] == "c1"
    assert item["parent_id"] is None
    assert "id" in item
    assert "path" in item
    assert "level" in item


def test_get_organization_units_hierarchy(client, session):
    """
    Test GET /organization_units with a hierarchy (parent and child).
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    root = OrganizationUnit(name="Root", company_id="c1")
    session.add(root)
    session.commit()
    child = OrganizationUnit(name="Child", company_id="c1", parent_id=root.id)
    session.add(child)
    session.commit()
    # Met à jour path/level
    root.update_path_and_level()
    child.update_path_and_level()
    session.commit()

    response = client.get("/organization_units")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    # On doit avoir au moins 2 unités
    assert len(data) >= 2
    # Vérifie que chaque unité a les bons champs
    for item in data:
        assert "id" in item
        assert "name" in item
        assert "company_id" in item
        assert "description" in item
        assert "parent_id" in item
        assert "path" in item
        assert "level" in item
    # Vérifie la cohérence parent/enfant
    root_item = next(x for x in data if x["name"] == "Root")
    child_item = next(x for x in data if x["name"] == "Child")
    assert child_item["parent_id"] == root_item["id"]
    assert child_item["level"] == root_item["level"] + 1
    assert child_item["path"].startswith(root_item["path"])


def test_get_organization_units_multiple_companies(client, session):
    """
    Test GET /organization_units with units from different companies.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org1 = OrganizationUnit(name="UnitA", company_id="c1")
    org2 = OrganizationUnit(name="UnitB", company_id="c2")
    session.add_all([org1, org2])
    session.commit()
    response = client.get("/organization_units")
    assert response.status_code == 200
    data = response.get_json()
    names = [item["name"] for item in data]
    assert "UnitA" in names
    assert "UnitB" in names


##################################################
# Test cases for POST /organization_units
##################################################
def test_post_organization_unit_success(client):
    """
    Test POST /organization_units with minimal valid data (racine).
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"name": "RootUnit", "company_id": "c1"}
    response = client.post("/organization_units", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "RootUnit"
    assert data["company_id"] == "c1"
    assert data["parent_id"] is None
    assert data["level"] == 0
    assert data["path"] == data["id"]


def test_post_organization_unit_with_parent(client, session):
    """
    Test POST /organization_units with a parent_id (enfant).
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    parent = OrganizationUnit(name="Parent", company_id="c1")
    session.add(parent)
    session.commit()
    parent.update_path_and_level()
    session.commit()

    payload = {"name": "ChildUnit", "company_id": "c1", "parent_id": parent.id}
    response = client.post("/organization_units", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["parent_id"] == parent.id
    assert data["level"] == parent.level + 1
    assert data["path"].startswith(parent.path)


def test_post_organization_unit_missing_name(client):
    """
    Test POST /organization_units with missing required 'name'.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"company_id": "c1"}
    response = client.post("/organization_units", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in data["error"]


def test_post_organization_unit_missing_company_id(client):
    """
    Test POST /organization_units with missing required 'company_id'.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"name": "NoCompany"}
    response = client.post("/organization_units", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "company_id" in data["error"]


def test_post_organization_unit_name_too_long(client):
    """
    Test POST /organization_units with name too long.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"name": "a" * 101, "company_id": "c1"}
    response = client.post("/organization_units", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in data["error"]


def test_post_organization_unit_invalid_parent_id(client):
    """
    Test POST /organization_units with invalid parent_id format.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"name": "Unit", "company_id": "c1", "parent_id": "not-a-uuid"}
    response = client.post("/organization_units", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "parent_id" in data["error"]


def test_post_organization_unit_cycle(client):
    """
    Test POST /organization_units with parent_id == self.id (cycle direct).
    """
    fake_id = str(uuid.uuid4())
    payload = {"name": "Cycle", "company_id": "c1", "parent_id": fake_id}
    # On patch le schéma pour simuler current_id == parent_id
    from app.schemas.organization_unit_schema import OrganizationUnitSchema

    org_unit_schema = OrganizationUnitSchema()
    org_unit_schema.context = {"current_id": fake_id}
    with pytest.raises(Exception):
        org_unit_schema.validate_parent_id(fake_id)


def test_post_organization_unit_unknown_field(client):
    """
    Test POST /organization_units with an unknown field.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    payload = {"name": "Unit", "company_id": "c1", "unknown": "value"}
    response = client.post("/organization_units", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "unknown" in data["error"]


##################################################
# Test cases for GET /organization_units/<id>
##################################################


def test_get_organization_unit_by_id_success(client, session):
    """
    Test GET /organization_units/<id> for an existing unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="UnitX", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    response = client.get(f"/organization_units/{org.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == org.id
    assert data["name"] == "UnitX"
    assert data["company_id"] == "c1"
    assert data["parent_id"] is None
    assert data["level"] == 0
    assert data["path"] == org.id


def test_get_organization_unit_by_id_with_parent(client, session):
    """
    Test GET /organization_units/<id> for a child unit with a parent.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    parent = OrganizationUnit(name="Parent", company_id="c1")
    session.add(parent)
    session.commit()
    parent.update_path_and_level()
    session.commit()

    child = OrganizationUnit(
        name="Child", company_id="c1", parent_id=parent.id
    )
    session.add(child)
    session.commit()
    child.update_path_and_level()
    session.commit()

    response = client.get(f"/organization_units/{child.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == child.id
    assert data["parent_id"] == parent.id
    assert data["level"] == parent.level + 1
    assert data["path"].startswith(parent.path)


def test_get_organization_unit_by_id_not_found(client):
    """
    Test GET /organization_units/<id> for a non-existent unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    response = client.get(f"/organization_units/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Organization unit not found"


##################################################
# Test cases for GET /organization_units/<id>/children
##################################################
def test_get_organization_unit_children_empty(client, session):
    """
    Test GET /organization_units/<id>/children when the unit has no children.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    parent = OrganizationUnit(name="Parent", company_id="c1")
    session.add(parent)
    session.commit()
    parent.update_path_and_level()
    session.commit()

    response = client.get(f"/organization_units/{parent.id}/children")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_organization_unit_children_with_children(client, session):
    """
    Test GET /organization_units/<id>/children when the unit has children.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    parent = OrganizationUnit(name="Parent", company_id="c1")
    session.add(parent)
    session.commit()
    parent.update_path_and_level()
    session.commit()

    child1 = OrganizationUnit(
        name="Child1", company_id="c1", parent_id=parent.id
    )
    child2 = OrganizationUnit(
        name="Child2", company_id="c1", parent_id=parent.id
    )
    session.add_all([child1, child2])
    session.commit()
    child1.update_path_and_level()
    child2.update_path_and_level()
    session.commit()

    response = client.get(f"/organization_units/{parent.id}/children")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    names = [item["name"] for item in data]
    assert "Child1" in names
    assert "Child2" in names
    for item in data:
        assert item["parent_id"] == parent.id


def test_get_organization_unit_children_not_found(client):
    """
    Test GET /organization_units/<id>/children for a non-existent unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    response = client.get(f"/organization_units/{fake_id}/children")
    # Selon l'implémentation, peut retourner 200 (liste vide) ou 404
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0
    else:
        data = response.get_json()
        assert "error" in data


##################################################
# Test cases for PUT /organization_units/<id>
##################################################
def test_put_organization_unit_success(client, session):
    """
    Test PUT /organization_units/<id> for a full update.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="OldName", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    payload = {"name": "NewName", "company_id": "c1"}
    response = client.put(f"/organization_units/{org.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == org.id
    assert data["name"] == "NewName"
    assert data["company_id"] == "c1"
    assert data["parent_id"] is None
    assert data["level"] == 0
    assert data["path"] == org.id


def test_put_organization_unit_change_parent(client, session):
    """
    Test PUT /organization_units/<id> to change the parent_id.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    parent = OrganizationUnit(name="Parent", company_id="c1")
    child = OrganizationUnit(name="Child", company_id="c1")
    session.add_all([parent, child])
    session.commit()
    parent.update_path_and_level()
    child.update_path_and_level()
    session.commit()

    payload = {"name": "Child", "company_id": "c1", "parent_id": parent.id}
    response = client.put(f"/organization_units/{child.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["parent_id"] == parent.id
    assert data["level"] == parent.level + 1
    assert data["path"].startswith(parent.path)


def test_put_organization_unit_not_found(client):
    """
    Test PUT /organization_units/<id> for a non-existent unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    payload = {"name": "DoesNotExist", "company_id": "c1"}
    response = client.put(f"/organization_units/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Organization unit not found"


def test_put_organization_unit_invalid_parent_id(client, session):
    """
    Test PUT /organization_units/<id> with invalid parent_id format.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="Unit", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    payload = {"name": "Unit", "company_id": "c1", "parent_id": "not-a-uuid"}
    response = client.put(f"/organization_units/{org.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "parent_id" in data["error"]


def test_put_organization_unit_cycle(client, session):
    """
    Test PUT /organization_units/<id> with parent_id == self.id (cycle direct).
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="Cycle", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    payload = {"name": "Cycle", "company_id": "c1", "parent_id": org.id}
    response = client.put(f"/organization_units/{org.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "parent_id" in data["error"]


##################################################
# Test cases for PATCH /organization_units/<id>
##################################################
def test_patch_organization_unit_success(client, session):
    """
    Test PATCH /organization_units/<id> for a partial update (name only).
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="PatchMe", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    payload = {"name": "PatchedName"}
    response = client.patch(f"/organization_units/{org.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == org.id
    assert data["name"] == "PatchedName"
    assert data["company_id"] == "c1"  # unchanged
    assert data["parent_id"] is None


def test_patch_organization_unit_change_parent(client, session):
    """
    Test PATCH /organization_units/<id> to change the parent_id only.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    parent = OrganizationUnit(name="Parent", company_id="c1")
    child = OrganizationUnit(name="Child", company_id="c1")
    session.add_all([parent, child])
    session.commit()
    parent.update_path_and_level()
    child.update_path_and_level()
    session.commit()

    payload = {"parent_id": parent.id}
    response = client.patch(f"/organization_units/{child.id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["parent_id"] == parent.id
    assert data["level"] == parent.level + 1
    assert data["path"].startswith(parent.path)


def test_patch_organization_unit_not_found(client):
    """
    Test PATCH /organization_units/<id> for a non-existent unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    payload = {"name": "Nope"}
    response = client.patch(f"/organization_units/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Organization unit not found"


def test_patch_organization_unit_invalid_parent_id(client, session):
    """
    Test PATCH /organization_units/<id> with invalid parent_id format.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="PatchUnit", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    payload = {"parent_id": "not-a-uuid"}
    response = client.patch(f"/organization_units/{org.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "parent_id" in data["error"]


def test_patch_organization_unit_cycle(client, session):
    """
    Test PATCH /organization_units/<id> with parent_id == self.id (cycle direct).
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    org = OrganizationUnit(name="PatchCycle", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    payload = {"parent_id": org.id}
    response = client.patch(f"/organization_units/{org.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "parent_id" in data["error"]


##################################################
# Test cases for DELETE /organization_units/<id>
##################################################
def test_delete_organization_unit_success(client, session):
    """
    Test DELETE /organization_units/<id> for an existing unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")
    org = OrganizationUnit(name="ToDelete", company_id="c1")
    session.add(org)
    session.commit()
    org.update_path_and_level()
    session.commit()

    response = client.delete(f"/organization_units/{org.id}")
    assert response.status_code == 204

    # Vérifie que l'unité n'existe plus
    get_response = client.get(f"/organization_units/{org.id}")
    assert get_response.status_code == 404


def test_delete_organization_unit_with_children(client, session):
    """
    Test DELETE /organization_units/<id> for a unit with children (suppression récursive).
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    parent = OrganizationUnit(name="ParentToDelete", company_id="c1")
    session.add(parent)
    session.commit()
    parent.update_path_and_level()
    session.commit()

    child = OrganizationUnit(
        name="ChildToDelete", company_id="c1", parent_id=parent.id
    )
    session.add(child)
    session.commit()
    child.update_path_and_level()
    session.commit()

    response = client.delete(f"/organization_units/{parent.id}")
    assert response.status_code == 204

    # Vérifie que le parent et l'enfant sont supprimés
    get_parent = client.get(f"/organization_units/{parent.id}")
    get_child = client.get(f"/organization_units/{child.id}")
    assert get_parent.status_code == 404
    assert get_child.status_code == 404


def test_delete_organization_unit_not_found(client):
    """
    Test DELETE /organization_units/<id> for a non-existent unit.
    """
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    jwt_token = create_jwt_token(str(company_id), str(user_id))
    client.set_cookie("access_token", jwt_token, domain="localhost")

    fake_id = str(uuid.uuid4())
    response = client.delete(f"/organization_units/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Organization unit not found"
