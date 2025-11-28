"""
Test simple pour vérifier le format de réponse Guardian.
"""

import uuid
from unittest import mock

from tests.test_user import get_init_db_payload, create_jwt_token


def test_guardian_direct_list_format(client):
    """Test que le service Guardian retourne une liste directe."""
    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response as direct list (comme dans l'erreur)
    junction_list = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": "admin"},
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": "user"},
    ]

    # Mock enriched role objects
    admin_role = {
        "id": "admin",
        "name": "Admin",
        "description": "Administrator",
    }
    user_role = {"id": "user", "name": "User", "description": "Regular user"}

    def mock_get_side_effect(url, **kwargs):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        if "/user-roles" in url:
            mock_resp.json.return_value = (
                junction_list  # Liste directe comme Guardian renvoie
            )
        elif "/roles/admin" in url:
            mock_resp.json.return_value = admin_role
        elif "/roles/user" in url:
            mock_resp.json.return_value = user_role
        return mock_resp

    with mock.patch("requests.get", side_effect=mock_get_side_effect):
        with mock.patch.dict(
            "os.environ", {"GUARDIAN_SERVICE_URL": "http://guardian:5000"}
        ):
            response = client.get(f"/users/{user_id}/roles")

            # Verify no error occurs
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert isinstance(data["roles"], list)
            assert len(data["roles"]) == 2
            # Now we expect enriched role objects with name and description
            assert data["roles"][0]["id"] == "admin"
            assert data["roles"][0]["name"] == "Admin"
            assert data["roles"][1]["id"] == "user"
            assert data["roles"][1]["name"] == "User"

            print("✅ Guardian direct list format handled successfully!")
            print(f"Response: {data}")


if __name__ == "__main__":
    # Test de la logique de détection
    test_cases = [
        # Cas 1: Liste directe (comme Guardian renvoie selon l'erreur)
        [{"id": "role1", "role_id": "admin"}],
        # Cas 2: Objet avec clé roles (ancien format)
        {"roles": [{"id": "role1", "role_id": "admin"}]},
        # Cas 3: Liste vide
        [],
        # Cas 4: Objet avec liste vide
        {"roles": []},
    ]

    for i, response_data in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {response_data}")

        # Logique de notre correction
        if isinstance(response_data, list):
            roles = response_data
            print(f"  -> Détecté comme liste directe: {len(roles)} rôles")
        elif isinstance(response_data, dict) and "roles" in response_data:
            roles = response_data.get("roles", [])
            print(
                f"  -> Détecté comme objet avec clé 'roles': {len(roles)} rôles"
            )
        else:
            print("  -> ❌ Format non supporté")
            continue

        print(f"  -> Roles extraits: {roles}")
