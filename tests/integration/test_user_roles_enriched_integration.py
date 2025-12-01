# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Tests d'intégration pour la structure enrichie des UserRoles (Issue #73).

Ces tests vérifient que GET /users/{user_id}/roles retourne la structure enrichie
avec un Guardian Service réel :
- Métadonnées de la jonction (id, user_id, role_id, created_at)
- Objet role imbriqué avec les détails du rôle (id, name, description, company_id)

⚠️ Nécessite Guardian Service en cours d'exécution.
   Utiliser: ./scripts/run-integration-tests.sh
"""

import os

import pytest
import requests


def is_guardian_available():
    """Vérifie si Guardian Service est disponible."""
    guardian_url = os.environ.get(
        "GUARDIAN_SERVICE_URL", "http://guardian:8000"
    )
    try:
        response = requests.get(f"{guardian_url}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_guardian_available(),
    reason="Guardian Service non disponible - test d'intégration skipped",
)


@pytest.mark.integration
def test_user_roles_enriched_structure(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : GET /users/{user_id}/roles avec structure enrichie (Issue #73).

    Vérifie que :
    1. La réponse contient les métadonnées de jonction (id, user_id, role_id, created_at)
    2. Chaque user_role contient un objet role imbriqué avec les détails du rôle
    3. Le frontend peut utiliser user_role.id pour DELETE
    4. Le frontend peut afficher user_role.role.name

    ⚠️ Nécessite Guardian Service configuré avec des rôles.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Test GET user roles
    response = integration_client.get(f"/users/{user_id}/roles")

    # Should succeed (user should have companyadmin role from guardian_init)
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.get_json()}"
    data = response.get_json()

    assert "roles" in data, "Response should contain 'roles' key"
    assert isinstance(data["roles"], list), "Roles should be a list"

    # User should have at least the companyadmin role
    assert (
        len(data["roles"]) > 0
    ), "User should have at least one role (companyadmin)"

    # Verify enriched structure for each user role (Issue #73)
    for user_role in data["roles"]:
        # ===== Junction metadata (for DELETE operations) =====
        assert (
            "id" in user_role
        ), "Each user role should have a junction 'id' field (for DELETE)"
        assert (
            "user_id" in user_role
        ), "Each user role should have a 'user_id' field"
        assert (
            "role_id" in user_role
        ), "Each user role should have a 'role_id' field"
        assert (
            "created_at" in user_role
        ), "Each user role should have a 'created_at' field"

        # ===== Nested role object from Guardian (for display) =====
        assert (
            "role" in user_role
        ), "Each user role should have a nested 'role' object"
        role = user_role["role"]

        # Verify role details
        assert "id" in role, "Nested role should have an 'id' field"
        assert "name" in role, "Nested role should have a 'name' field"
        # Optional but expected fields
        assert (
            "description" in role
        ), "Nested role should have a 'description' field"
        assert (
            "company_id" in role
        ), "Nested role should have a 'company_id' field"

        # ===== Verify IDs are different (junction_id != role_id) =====
        junction_id = user_role["id"]
        role_id_in_role = role["id"]
        role_id_in_junction = user_role["role_id"]

        # The role_id in junction should match the role.id
        assert (
            role_id_in_junction == role_id_in_role
        ), "role_id should match role.id"

        # Junction ID should be different from role ID
        # (This is critical for DELETE operations to work correctly)
        assert (
            junction_id != role_id_in_role
        ), f"Junction ID ({junction_id}) should be different from role ID ({role_id_in_role})"

        print(
            f"✅ UserRole structure valid: junction_id={junction_id}, "
            f"role_id={role_id_in_role}, role_name={role['name']}"
        )

    # Extract useful information for logging
    junction_ids = [user_role["id"] for user_role in data["roles"]]
    role_names = [user_role["role"]["name"] for user_role in data["roles"]]

    print(f"✅ User roles retrieved: {len(junction_ids)} enriched user roles")
    print(f"   Junction IDs: {junction_ids}")
    print(f"   Role names: {role_names}")


@pytest.mark.integration
def test_user_roles_enriched_allows_correct_delete(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : Vérifier que l'ID retourné permet un DELETE correct.

    Issue #73 : Le problème original était que l'ID retourné était celui du rôle,
    pas celui de la jonction, ce qui empêchait le DELETE de fonctionner.

    Ce test vérifie que :
    1. L'endpoint retourne bien le junction_id au niveau racine
    2. Ce junction_id est différent du role.id
    3. Le frontend peut utiliser cet ID pour construire l'URL DELETE correcte

    ⚠️ Nécessite Guardian Service configuré.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Get user roles
    response = integration_client.get(f"/users/{user_id}/roles")
    assert response.status_code == 200
    data = response.get_json()

    if len(data["roles"]) > 0:
        user_role = data["roles"][0]

        # Verify we have the junction ID (not the role ID)
        junction_id = user_role["id"]
        role_id = user_role["role"]["id"]

        # These must be different
        assert (
            junction_id != role_id
        ), "Junction ID and Role ID must be different for DELETE to work"

        # The URL for DELETE should use the junction ID
        delete_url = f"/users/{user_id}/roles/{junction_id}"

        print(
            f"✅ DELETE URL constructed correctly: {delete_url} (junction_id={junction_id}, role_id={role_id})"
        )

        # Note: We don't actually DELETE in this test to avoid breaking other tests
        # The important thing is that we can construct the correct URL

    else:
        print("⚠️ No roles found for user, skipping DELETE URL verification")


@pytest.mark.integration
def test_user_roles_enriched_allows_display_role_name(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : Vérifier que le nom du rôle est accessible pour l'affichage.

    Issue #73 : Le frontend doit pouvoir afficher le nom du rôle via user_role.role.name

    Ce test vérifie que :
    1. Chaque user_role contient un objet role imbriqué
    2. L'objet role contient le champ name
    3. Le frontend peut afficher role.name au lieu de chercher le nom ailleurs

    ⚠️ Nécessite Guardian Service configuré.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Get user roles
    response = integration_client.get(f"/users/{user_id}/roles")
    assert response.status_code == 200
    data = response.get_json()

    if len(data["roles"]) > 0:
        for user_role in data["roles"]:
            # Verify role name is accessible
            assert (
                "role" in user_role
            ), "user_role should have nested 'role' object"
            assert "name" in user_role["role"], "role should have 'name' field"

            role_name = user_role["role"]["name"]
            junction_id = user_role["id"]

            # Frontend can now do:
            # display_text = f"Role: {user_role['role']['name']}"  ✅
            # delete_id = user_role['id']  ✅

            print(
                f"✅ Role display: name={role_name}, junction_id={junction_id}"
            )

            # Verify role name is not empty
            assert (
                role_name
            ), "Role name should not be empty for proper display"

    else:
        print("⚠️ No roles found for user, skipping display verification")
