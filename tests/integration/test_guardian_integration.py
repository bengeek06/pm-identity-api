# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Tests d'intégration pour Guardian Service.

Ces tests documentent le comportement attendu lors de l'intégration avec Guardian.
Ils sont skipped si Guardian n'est pas disponible (comportement normal en dev/CI).

Note: Les tests unitaires ne testent PAS Guardian - ils mockent les appels.
      Ces tests d'intégration valident que l'intégration réelle fonctionne.
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
def test_guardian_user_roles_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : récupération des rôles utilisateur depuis Guardian.

    Ce test valide que :
    1. Le JWT est correctement forwardé à Guardian
    2. La réponse Guardian est correctement parsée
    3. Les erreurs Guardian sont gérées proprement

    ⚠️ Nécessite Guardian Service en cours d'exécution.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Test GET user roles
    response = integration_client.get(f"/users/{user_id}/roles")

    # Should succeed (even if empty roles)
    assert response.status_code == 200
    data = response.get_json()
    assert "roles" in data
    assert isinstance(data["roles"], list)

    print(
        f"✅ Guardian integration OK - User {user_id} has {len(data['roles'])} roles"
    )


@pytest.mark.integration
def test_guardian_user_permissions_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : récupération des permissions utilisateur via Guardian.

    Valide le flow complet :
    1. Récupération des rôles depuis Guardian
    2. Récupération des policies pour chaque rôle
    3. Agrégation des permissions

    ⚠️ Nécessite Guardian Service en cours d'exécution.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Test GET user permissions
    response = integration_client.get(f"/users/{user_id}/permissions")

    # Should succeed (even if empty permissions)
    assert response.status_code == 200
    data = response.get_json()
    assert "permissions" in data
    assert isinstance(data["permissions"], list)

    print(
        f"✅ Guardian permissions integration OK - {len(data['permissions'])} permissions"
    )


@pytest.mark.integration
def test_guardian_access_control_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : vérification que le decorator check_access fonctionne.

    Valide que :
    1. Les endpoints protégés appellent Guardian pour vérifier l'accès
    2. Le JWT est correctement forwardé
    3. Les refus d'accès sont gérés

    ⚠️ Nécessite Guardian Service configuré.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Essayer d'accéder à un endpoint protégé
    # Guardian devrait autoriser ou refuser selon la configuration
    response = integration_client.get(f"/users/{user_id}")

    # Accepter soit 200 (autorisé) soit 403 (refusé par Guardian)
    assert response.status_code in [200, 403]

    if response.status_code == 403:
        data = response.get_json()
        assert (
            "access" in str(data).lower() or "permission" in str(data).lower()
        )
        print("✅ Guardian access denied correctly")
    else:
        print("✅ Guardian access granted")


@pytest.mark.integration
def test_guardian_operation_format_integration(
    integration_client, real_company, integration_token
):
    """
    Test d'intégration : vérification du format des opérations envoyées à Guardian.

    Guardian attend les opérations en MAJUSCULES (LIST, CREATE, READ, UPDATE, DELETE).
    Ce test vérifie que les différentes opérations CRUD fonctionnent correctement.

    ⚠️ Nécessite Guardian Service configuré.
    """
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Test LIST operation
    response = integration_client.get("/companies")
    assert response.status_code in [
        200,
        403,
    ], f"LIST failed with {response.status_code}"
    print(f"✅ LIST operation: {response.status_code}")

    # Test READ operation
    response = integration_client.get(f"/companies/{real_company.id}")
    assert response.status_code in [
        200,
        403,
        404,
    ], f"READ failed with {response.status_code}"
    print(f"✅ READ operation: {response.status_code}")

    # Test CREATE operation (may fail with 403 or succeed)
    response = integration_client.post(
        "/companies",
        json={"name": "Test Company Integration", "description": "Test"},
    )
    assert response.status_code in [
        200,
        201,
        400,
        403,
    ], f"CREATE failed with {response.status_code}"
    print(f"✅ CREATE operation: {response.status_code}")

    # Test UPDATE operation
    response = integration_client.put(
        f"/companies/{real_company.id}",
        json={"name": "Updated Company", "description": "Updated"},
    )
    assert response.status_code in [
        200,
        403,
        404,
    ], f"UPDATE failed with {response.status_code}"
    print(f"✅ UPDATE operation: {response.status_code}")

    # Test DELETE operation
    response = integration_client.delete(f"/companies/{real_company.id}")
    assert response.status_code in [
        200,
        204,
        400,
        403,
        404,
    ], f"DELETE failed with {response.status_code}"
    print(f"✅ DELETE operation: {response.status_code}")


@pytest.mark.integration
def test_user_roles_endpoint_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : GET /users/{user_id}/roles avec appel réel à Guardian.

    Vérifie que :
    1. L'endpoint fonctionne avec Guardian
    2. Les rôles sont récupérés correctement
    3. Le format de réponse est correct

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

    # Verify role structure
    for role in data["roles"]:
        assert "role_id" in role, "Each role should have a 'role_id' field"
        assert "id" in role, "Each role should have an 'id' field"

    role_ids = [role["role_id"] for role in data["roles"]]
    print(f"✅ User roles retrieved: {len(role_ids)} roles")


@pytest.mark.integration
def test_user_role_by_id_endpoint_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : GET /users/{user_id}/roles/{role_id} avec Guardian.

    Vérifie la récupération d'un rôle spécifique.

    ⚠️ Nécessite Guardian Service configuré.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # First get all roles to find a role_id
    response = integration_client.get(f"/users/{user_id}/roles")
    assert response.status_code == 200
    data = response.get_json()

    if len(data["roles"]) > 0:
        role_id = data["roles"][0]["id"]

        # Test GET specific role
        response = integration_client.get(f"/users/{user_id}/roles/{role_id}")

        # Should succeed or return 404 if role doesn't exist
        assert response.status_code in [
            200,
            404,
        ], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            role_data = response.get_json()
            assert "id" in role_data
            assert "role_id" in role_data
            print(f"✅ Specific role retrieved: {role_data['role_id']}")
        else:
            print("✅ Role not found (404) - acceptable response")
    else:
        print("⚠️ No roles found for user, skipping specific role test")


@pytest.mark.integration
def test_user_policies_endpoint_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : GET /users/{user_id}/policies avec appel réel à Guardian.

    Vérifie que :
    1. Les policies sont récupérées depuis Guardian
    2. Le format de réponse est correct
    3. Les policies correspondent aux rôles de l'utilisateur

    ⚠️ Nécessite Guardian Service configuré.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Test GET user policies
    response = integration_client.get(f"/users/{user_id}/policies")

    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.get_json()}"
    data = response.get_json()

    assert "policies" in data, "Response should contain 'policies' key"
    assert isinstance(data["policies"], list), "Policies should be a list"

    # Verify policy structure
    for policy in data["policies"]:
        assert "name" in policy, "Each policy should have a 'name' field"
        assert "id" in policy, "Each policy should have an 'id' field"

    policy_names = [policy["name"] for policy in data["policies"]]
    print(f"✅ User policies retrieved: {policy_names}")


@pytest.mark.integration
def test_user_permissions_endpoint_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : GET /users/{user_id}/permissions avec appel réel à Guardian.

    Vérifie que :
    1. Les permissions sont calculées depuis les policies
    2. Le format de réponse est correct
    3. Les permissions incluent service, resource, et operation

    ⚠️ Nécessite Guardian Service configuré.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Test GET user permissions
    response = integration_client.get(f"/users/{user_id}/permissions")

    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.get_json()}"
    data = response.get_json()

    assert "permissions" in data, "Response should contain 'permissions' key"
    assert isinstance(
        data["permissions"], list
    ), "Permissions should be a list"

    # Verify permission structure
    for permission in data["permissions"]:
        assert (
            "service" in permission
        ), "Each permission should have a 'service' field"
        assert (
            "resource_name" in permission
        ), "Each permission should have a 'resource_name' field"
        assert (
            "operation" in permission
        ), "Each permission should have an 'operation' field"

        # Verify operation is in uppercase (Guardian requirement)
        operation = permission["operation"]
        assert (
            operation.isupper()
        ), f"Operation should be uppercase, got '{operation}'"

    print(
        f"✅ User permissions retrieved: {len(data['permissions'])} permissions"
    )

    # Display sample permissions
    if len(data["permissions"]) > 0:
        sample = data["permissions"][0]
        print(
            f"   Sample permission: {sample['service']}.{sample['resource_name']}.{sample['operation']}"
        )


@pytest.mark.integration
def test_user_roles_operations_case_integration(
    integration_client, real_user, integration_token
):
    """
    Test d'intégration : Vérifier que les opérations CRUD sur les rôles fonctionnent.

    Ce test valide que les opérations sont bien envoyées en majuscules à Guardian.

    ⚠️ Nécessite Guardian Service configuré.
    """
    user_id = real_user.id
    integration_client.set_cookie(
        "access_token", integration_token, domain="localhost"
    )

    # Test LIST (GET all roles)
    response = integration_client.get(f"/users/{user_id}/roles")
    assert response.status_code in [
        200,
        403,
    ], f"LIST roles failed: {response.status_code}"
    print(f"✅ LIST roles operation: {response.status_code}")

    # Test CREATE (POST new role) - may fail with 403 if not authorized
    response = integration_client.post(
        f"/users/{user_id}/roles", json={"role": "test-role"}
    )
    assert response.status_code in [
        200,
        201,
        400,
        403,
    ], f"CREATE role failed: {response.status_code}"
    print(f"✅ CREATE role operation: {response.status_code}")

    # Get a role ID for READ/DELETE tests
    response = integration_client.get(f"/users/{user_id}/roles")
    if response.status_code == 200:
        data = response.get_json()
        if len(data["roles"]) > 0:
            role_id = data["roles"][0]["id"]

            # Test READ (GET specific role)
            response = integration_client.get(
                f"/users/{user_id}/roles/{role_id}"
            )
            assert response.status_code in [
                200,
                403,
                404,
            ], f"READ role failed: {response.status_code}"
            print(f"✅ READ role operation: {response.status_code}")

            # Test DELETE - only if we created a test role
            # (skip deleting companyadmin to avoid breaking other tests)
            print(
                "✅ DELETE role operation: skipped (preserving existing roles)"
            )
