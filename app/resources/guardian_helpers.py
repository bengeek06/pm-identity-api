# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
module: app.resources.guardian_helpers

Helper functions for interacting with Guardian Service.
Provides common functionality for fetching roles, policies, and permissions.
"""

import requests
from flask import current_app, g, request

from app.logger import logger
from app.models.user import User


def validate_user_access(user_id):
    """
    Validate that the requesting user can access the target user's data.

    Reads user_id and company_id directly from Flask's g object
    (populated by require_jwt_auth decorator).

    Args:
        user_id (str): The ID of the target user

    Returns:
        tuple: (None, None) on success
        tuple: (error_dict, status_code) on failure
    """
    requesting_user_id = getattr(g, "user_id", None)
    company_id = getattr(g, "company_id", None)

    if not requesting_user_id:
        logger.error("user_id missing in JWT")
        return {"message": "user_id missing in JWT"}, 400

    # Verify that the requested user exists and belongs to the same company
    target_user = User.get_by_id(user_id)
    if not target_user:
        logger.error("User %s not found", user_id)
        return {"message": "User not found"}, 404

    if target_user.company_id != company_id:
        logger.warning(
            "User %s attempted to access data for user %s from different company",
            requesting_user_id,
            user_id,
        )
        return {"message": "Access denied"}, 403

    return None, None


def get_guardian_headers():
    """
    Get headers for Guardian Service requests with JWT forwarding.

    Returns:
        dict: Headers dictionary with JWT cookie if available
    """
    jwt_token = request.cookies.get("access_token")
    headers = {}
    if jwt_token:
        headers["Cookie"] = f"access_token={jwt_token}"
    return headers


def normalize_guardian_response(response_data, key):
    """
    Normalize Guardian Service response to a list.

    Guardian may return either a direct list or a dict with a key.

    Args:
        response_data: Response data from Guardian (list or dict)
        key (str): The key to look for in dict responses

    Returns:
        list: Normalized list of items
    """
    if isinstance(response_data, list):
        return response_data
    if isinstance(response_data, dict) and key in response_data:
        return response_data.get(key, [])

    logger.warning(
        "Unexpected %s response format from Guardian: %s", key, response_data
    )
    return []


def fetch_user_roles(user_id, guardian_url, headers):
    """
    Fetch all roles for a user from Guardian Service.

    Args:
        user_id (str): The user ID
        guardian_url (str): Guardian Service base URL
        headers (dict): Request headers

    Returns:
        tuple: (list of roles, None) on success
        tuple: (None, error_tuple) on failure where error_tuple is (error_dict, status_code)
    """
    try:
        roles_response = requests.get(
            f"{guardian_url}/user-roles",
            params={"user_id": user_id},
            headers=headers,
            timeout=current_app.config.get("GUARDIAN_SERVICE_TIMEOUT", 5),
        )
    except requests.exceptions.RequestException as e:
        logger.error("Error contacting Guardian service for roles: %s", str(e))
        return None, ({"message": "Error fetching user roles"}, 500)

    if roles_response.status_code != 200:
        logger.error(
            "Error fetching roles from Guardian: %s", roles_response.text
        )
        return None, ({"message": "Error fetching user roles"}, 500)

    roles_data = roles_response.json()
    logger.debug("Guardian roles response data: %s", roles_data)

    user_roles = normalize_guardian_response(roles_data, "roles")
    return user_roles, None


def fetch_policies_for_role(role_id, guardian_url, headers):
    """
    Fetch policies for a specific role from Guardian Service.

    Args:
        role_id (str): The role ID
        guardian_url (str): Guardian Service base URL
        headers (dict): Request headers

    Returns:
        list: List of policies (empty list if error or not found)
    """
    try:
        policies_response = requests.get(
            f"{guardian_url}/roles/{role_id}/policies",
            headers=headers,
            timeout=current_app.config.get("GUARDIAN_SERVICE_TIMEOUT", 5),
        )
    except requests.exceptions.RequestException as e:
        logger.error(
            "Error contacting Guardian service for policies of role %s: %s",
            role_id,
            str(e),
        )
        return []

    if policies_response.status_code == 404:
        logger.warning("Role %s not found in Guardian, skipping", role_id)
        return []

    if policies_response.status_code != 200:
        logger.error(
            "Error fetching policies for role %s from Guardian: %s",
            role_id,
            policies_response.text,
        )
        return []

    policies_data = policies_response.json()
    logger.debug(
        "Guardian policies response for role %s: %s", role_id, policies_data
    )

    return normalize_guardian_response(policies_data, "policies")


def fetch_policies_for_roles(user_roles, guardian_url, headers):
    """
    Fetch all policies for a list of user roles from Guardian Service.

    Args:
        user_roles (list): List of user role objects
        guardian_url (str): Guardian Service base URL
        headers (dict): Request headers

    Returns:
        set: Set of unique policy IDs
        list: List of unique policy objects (for policies endpoint)
    """
    all_policy_ids = set()
    all_policies = []
    seen_policy_ids = set()

    for user_role in user_roles:
        role_id = user_role.get("role_id")
        if not role_id:
            logger.warning("user_role missing role_id: %s", user_role)
            continue

        policies = fetch_policies_for_role(role_id, guardian_url, headers)

        # Collect policies and deduplicate
        for policy in policies:
            policy_id = policy.get("id")
            if policy_id:
                all_policy_ids.add(policy_id)
                if policy_id not in seen_policy_ids:
                    seen_policy_ids.add(policy_id)
                    all_policies.append(policy)

    return all_policy_ids, all_policies


def fetch_permissions_for_policy(policy_id, guardian_url, headers):
    """
    Fetch permissions for a specific policy from Guardian Service.

    Args:
        policy_id (str): The policy ID
        guardian_url (str): Guardian Service base URL
        headers (dict): Request headers

    Returns:
        list: List of permissions (empty list if error or not found)
    """
    try:
        permissions_response = requests.get(
            f"{guardian_url}/policies/{policy_id}/permissions",
            headers=headers,
            timeout=current_app.config.get("GUARDIAN_SERVICE_TIMEOUT", 5),
        )
    except requests.exceptions.RequestException as e:
        logger.error(
            "Error contacting Guardian service for permissions of policy %s: %s",
            policy_id,
            str(e),
        )
        return []

    if permissions_response.status_code == 404:
        logger.warning("Policy %s not found in Guardian, skipping", policy_id)
        return []

    if permissions_response.status_code != 200:
        logger.error(
            "Error fetching permissions for policy %s from Guardian: %s",
            policy_id,
            permissions_response.text,
        )
        return []

    permissions_data = permissions_response.json()
    logger.debug(
        "Guardian permissions response for policy %s: %s",
        policy_id,
        permissions_data,
    )

    return normalize_guardian_response(permissions_data, "permissions")


def fetch_role_details(role_id, guardian_url, headers):
    """
    Fetch full role details for a specific role from Guardian Service.

    Args:
        role_id (str): The role ID
        guardian_url (str): Guardian Service base URL
        headers (dict): Request headers

    Returns:
        dict: Full role object with all fields, or minimal dict with just role_id if error
    """
    try:
        role_response = requests.get(
            f"{guardian_url}/roles/{role_id}",
            headers=headers,
            timeout=current_app.config.get("GUARDIAN_SERVICE_TIMEOUT", 5),
        )
    except requests.exceptions.RequestException as e:
        logger.error(
            "Error contacting Guardian service for role %s: %s",
            role_id,
            str(e),
        )
        # Return minimal valid structure with required fields
        return {
            "id": role_id,
            "name": f"Unknown Role ({role_id})",
            "description": "Role details unavailable",
            "company_id": None,
        }

    if role_response.status_code == 404:
        logger.warning("Role %s not found in Guardian", role_id)
        # Return minimal valid structure for not found roles
        return {
            "id": role_id,
            "name": f"Unknown Role ({role_id})",
            "description": "Role not found in Guardian",
            "company_id": None,
        }

    if role_response.status_code != 200:
        logger.error(
            "Error fetching role %s from Guardian: %s",
            role_id,
            role_response.text,
        )
        # Return minimal valid structure for errors
        return {
            "id": role_id,
            "name": f"Unknown Role ({role_id})",
            "description": "Error fetching role details",
            "company_id": None,
        }

    role_data = role_response.json()
    logger.debug("Guardian role response for role %s: %s", role_id, role_data)

    return role_data
