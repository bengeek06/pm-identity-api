"""
Test simple pour vérifier le format de réponse Guardian.
"""

import uuid
from unittest import mock

from tests.unit.conftest import create_jwt_token, get_init_db_payload


def test_guardian_direct_list_format(client, app):
    """Test que le service Guardian retourne une liste directe."""
    # Enable Guardian Service for this test
    app.config["USE_GUARDIAN_SERVICE"] = True
    app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"

    # Create test data
    init_db_payload = get_init_db_payload()
    resp = client.post("/init-db", json=init_db_payload)
    assert resp.status_code == 201
    company_id = resp.get_json()["company"]["id"]
    user_id = resp.get_json()["user"]["id"]

    jwt_token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", jwt_token, domain="localhost")

    # Mock Guardian service response for check_access
    mock_check_access = mock.Mock()
    mock_check_access.status_code = 200
    mock_check_access.json.return_value = {
        "access_granted": True,
        "reason": "Access granted",
        "status": 200,
    }

    # Mock Guardian service response as direct list (comme dans l'erreur)
    roles_list = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": "admin"},
        {"id": str(uuid.uuid4()), "user_id": user_id, "role_id": "user"},
    ]

    mock_get_roles = mock.Mock()
    mock_get_roles.status_code = 200
    mock_get_roles.json.return_value = (
        roles_list  # Liste directe comme Guardian renvoie
    )

    with mock.patch("requests.get", side_effect=lambda url, **kwargs: mock_get_roles if "user-roles" in url else mock.Mock()):
        with mock.patch("requests.post", return_value=mock_check_access):
            response = client.get(f"/users/{user_id}/roles")

            # Verify no error occurs
            assert response.status_code == 200
            data = response.get_json()
            assert "roles" in data
            assert isinstance(data["roles"], list)
            assert len(data["roles"]) == 2
            assert data["roles"][0]["role_id"] == "admin"
            assert data["roles"][1]["role_id"] == "user"

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
