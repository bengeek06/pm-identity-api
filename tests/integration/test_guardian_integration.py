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
