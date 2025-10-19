"""
Tesst cases for the Subcontractor resource in the PM Identity API.
"""

import uuid
from app.models.subcontractor import Subcontractor
from app.schemas.subcontractor_schema import SubcontractorSchema

##################################################
# Test cases for GET /subcontractors
##################################################


def test_get_subcontractors_empty(client, session):
    """
    Test GET /subcontractors when there are no subcontractors.
    """
    response = client.get("/subcontractors")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_subcontractors_single(client, session):
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="SubA", company_id=company_id)
    session.add(sub)
    session.commit()
    response = client.get("/subcontractors")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "SubA"
    assert "id" in data[0]


def test_get_subcontractors_multiple(client, session):
    """
    Test GET /subcontractors with multiple subcontractors.
    """
    company_id = str(uuid.uuid4())
    sub1 = Subcontractor(name="SubA", company_id=company_id)
    sub2 = Subcontractor(name="SubB", company_id=company_id)
    session.add_all([sub1, sub2])
    session.commit()
    response = client.get("/subcontractors")
    assert response.status_code == 200
    data = response.get_json()
    names = [item["name"] for item in data]
    assert "SubA" in names
    assert "SubB" in names


##################################################
# Test cases for POST /subcontractors
##################################################


def test_post_subcontractor_success(client, session):
    """
    Test POST /subcontractors with valid data.
    """
    company_id = str(uuid.uuid4())
    payload = {"name": "NewSub", "company_id": company_id}
    response = client.post("/subcontractors", json=payload)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["name"] == "NewSub"
    assert data["company_id"] == company_id
    assert "id" in data


def test_post_subcontractor_missing_name(client, session):
    """
    Test POST /subcontractors with missing required 'name'.
    """
    company_id = str(uuid.uuid4())
    payload = {"company_id": company_id}
    response = client.post("/subcontractors", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in str(data).lower()


def test_post_subcontractor_duplicate_name(client, session):
    """
    Test POST /subcontractors with duplicate name if unique constraint exists.
    """
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="DupSub", company_id=company_id)
    session.add(sub)
    session.commit()
    payload = {"name": "DupSub", "company_id": company_id}
    response = client.post("/subcontractors", json=payload)
    # Si unique, 400 attendu, sinon 201
    assert response.status_code in (201, 400)


##################################################
# Test cases for GET /subcontractors/<id>
##################################################


def test_get_subcontractor_by_id_success(client, session):
    """
    Test GET /subcontractors/<id> for an existing subcontractor.
    """
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="SubGet", company_id=company_id)
    session.add(sub)
    session.commit()

    response = client.get(f"/subcontractors/{sub.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == sub.id
    assert data["name"] == "SubGet"


def test_get_subcontractor_by_id_not_found(client, session):
    """
    Test GET /subcontractors/<id> for a non-existent subcontractor.
    """
    fake_id = str(uuid.uuid4())
    response = client.get(f"/subcontractors/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data


##################################################
# Test cases for PUT /subcontractors/<id>
##################################################


def test_put_subcontractor_success(client, session):
    """
    Test PUT /subcontractors/<id> for a full update.
    """
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="OldSub", company_id=company_id)
    session.add(sub)
    session.commit()
    payload = {"name": "UpdatedSub", "company_id": company_id}
    response = client.put(f"/subcontractors/{sub.id}", json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["id"] == sub.id
    assert data["name"] == "UpdatedSub"


def test_put_subcontractor_not_found(client, session):
    """
    Test PUT /subcontractors/<id> for a non-existent subcontractor.
    """
    fake_id = str(uuid.uuid4())
    payload = {"name": "NoSub"}
    response = client.put(f"/subcontractors/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data


def test_put_subcontractor_missing_name(client, session):
    """
    Test PUT /subcontractors/<id> with missing required 'name'.
    """
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="ToBeUpdated", company_id=company_id)
    session.add(sub)
    session.commit()
    payload = {company_id: company_id}
    response = client.put(f"/subcontractors/{sub.id}", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "name" in str(data).lower()


##################################################
# Test cases for PATCH /subcontractors/<id>
##################################################


def test_patch_subcontractor_success(client, session):
    """
    Test PATCH /subcontractors/<id> for a partial update (name only).
    """
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="PatchSub", company_id=company_id)
    session.add(sub)
    session.commit()
    payload = {"name": "PatchedSub"}
    response = client.patch(f"/subcontractors/{sub.id}", json=payload)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["id"] == sub.id
    assert data["name"] == "PatchedSub"


def test_patch_subcontractor_not_found(client, session):
    """
    Test PATCH /subcontractors/<id> for a non-existent subcontractor.
    """
    fake_id = str(uuid.uuid4())
    payload = {"name": "NoPatch"}
    response = client.patch(f"/subcontractors/{fake_id}", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data


def test_patch_subcontractor_missing_name(client, session):
    """
    Test PATCH /subcontractors/<id> with missing required 'name'.
    """
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="PatchMissing", company_id=company_id)
    session.add(sub)
    session.commit()
    payload = {}
    response = client.patch(f"/subcontractors/{sub.id}", json=payload)
    # Selon l'implémentation, peut être 200 (pas de changement) ou 400 (si le champ est requis)
    assert response.status_code in (200, 400)
    if response.status_code == 400:
        data = response.get_json()
        assert "name" in str(data).lower()


##################################################
# Test cases for DELETE /subcontractors/<id>
##################################################


def test_delete_subcontractor_success(client, session):
    """
    Test DELETE /subcontractors/<id> for an existing subcontractor.
    """
    company_id = str(uuid.uuid4())
    sub = Subcontractor(name="ToDelete", company_id=company_id)
    session.add(sub)
    session.commit()

    response = client.delete(f"/subcontractors/{sub.id}")
    assert response.status_code == 204

    # Vérifie que le sous-traitant n'existe plus
    get_response = client.get(f"/subcontractors/{sub.id}")
    assert get_response.status_code == 404


def test_delete_subcontractor_not_found(client, session):
    """
    Test DELETE /subcontractors/<id> for a non-existent subcontractor.
    """
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/subcontractors/{fake_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data or "message" in data
