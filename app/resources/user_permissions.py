# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
module: app.resources.user_permissions

This module defines Flask-RESTful resources for aggregating permissions
associated with users via the Guardian Service.

It provides endpoints for retrieving all permissions assigned to a user
through their role and policy assignments.
"""

from flask import current_app
from flask_restful import Resource

from app.logger import logger
from app.resources.guardian_helpers import (
    fetch_permissions_for_policy,
    fetch_policies_for_roles,
    fetch_user_roles,
    get_guardian_headers,
    validate_user_access,
)
from app.utils import check_access_required, require_jwt_auth


class UserPermissionsResource(Resource):
    """
    Resource for retrieving all permissions associated with a user.

    This resource aggregates permissions from all policies of all roles
    assigned to a user by querying the Guardian service.

    Methods:
        get(user_id):
            Retrieve all permissions for a specific user.
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, user_id):
        """
        Retrieve all permissions associated with a user's policies.

        This endpoint:
        1. Fetches all roles assigned to the user from Guardian
        2. For each role, fetches associated policies from Guardian
        3. For each policy, fetches associated permissions from Guardian
        4. Returns a deduplicated list of all permissions

        Args:
            user_id (str): The ID of the user whose permissions to retrieve.

        Returns:
            tuple: JSON with permissions list and HTTP status code 200 on success.
            tuple: Error message and HTTP status code 400, 403, 404, or 500 on failure.
        """
        logger.info("Fetching permissions for user ID %s", user_id)

        # Validate user access
        error, status = validate_user_access(user_id)
        if error:
            return error, status

        # If Guardian Service is disabled, return empty permissions
        if not current_app.config.get("USE_GUARDIAN_SERVICE"):
            logger.debug(
                "Guardian Service is disabled - returning empty permissions list"
            )
            return {"permissions": []}, 200

        guardian_url = current_app.config["GUARDIAN_SERVICE_URL"]
        headers = get_guardian_headers()

        # Step 1: Fetch all roles for the user
        user_roles, error = fetch_user_roles(user_id, guardian_url, headers)
        if error:
            return error

        # Step 2: Fetch policies for each role
        all_policy_ids, _ = fetch_policies_for_roles(
            user_roles, guardian_url, headers
        )

        # Step 3: Fetch permissions for each policy
        all_permissions = []
        seen_permission_ids = set()

        for policy_id in all_policy_ids:
            permissions = fetch_permissions_for_policy(
                policy_id, guardian_url, headers
            )

            # Deduplicate permissions by ID
            for permission in permissions:
                permission_id = permission.get("id")
                if (
                    permission_id
                    and permission_id not in seen_permission_ids
                ):
                    seen_permission_ids.add(permission_id)
                    all_permissions.append(permission)

        logger.info(
            "Successfully fetched %d unique permissions for user %s",
            len(all_permissions),
            user_id,
        )
        return {"permissions": all_permissions}, 200
