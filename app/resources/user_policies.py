"""
module: app.resources.user_policies

This module defines Flask-RESTful resources for aggregating policies
associated with users via the Guardian Service.

It provides endpoints for retrieving all policies assigned to a user
through their role assignments.
"""

import os

import requests
from flask import g, request
from flask_restful import Resource

from app.logger import logger
from app.models.user import User
from app.utils import check_access_required, require_jwt_auth


class UserPoliciesResource(Resource):
    """
    Resource for retrieving all policies associated with a user.

    This resource aggregates policies from all roles assigned to a user
    by querying the Guardian service.

    Methods:
        get(user_id):
            Retrieve all policies for a specific user.
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(
        self, user_id
    ):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """
        Retrieve all policies associated with a user's roles.

        This endpoint:
        1. Fetches all roles assigned to the user from Guardian
        2. For each role, fetches associated policies from Guardian
        3. Returns a deduplicated list of all policies

        Args:
            user_id (str): The ID of the user whose policies to retrieve.

        Returns:
            tuple: JSON with policies list and HTTP status code 200 on success.
            tuple: Error message and HTTP status code 400, 403, 404, or 500 on failure.
        """
        logger.info("Fetching policies for user ID %s", user_id)

        jwt_data = getattr(g, "jwt_data", {})
        requesting_user_id = jwt_data.get("user_id")
        company_id = jwt_data.get("company_id")

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
                "User %s attempted to access policies for user %s from different company",
                requesting_user_id,
                user_id,
            )
            return {"message": "Access denied"}, 403

        guardian_url = os.environ.get("GUARDIAN_SERVICE_URL")
        if not guardian_url:
            logger.error("GUARDIAN_SERVICE_URL not set")
            return {"message": "Internal server error"}, 500

        # Get JWT token from cookies to forward to Guardian service
        jwt_token = request.cookies.get("access_token")
        headers = {}
        if jwt_token:
            headers["Cookie"] = f"access_token={jwt_token}"

        # Step 1: Fetch all roles for the user
        try:
            roles_response = requests.get(
                f"{guardian_url}/user-roles",
                params={"user_id": user_id},
                headers=headers,
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                "Error contacting Guardian service for roles: %s", str(e)
            )
            return {"message": "Error fetching user roles"}, 500

        if roles_response.status_code != 200:
            logger.error(
                "Error fetching roles from Guardian: %s", roles_response.text
            )
            return {"message": "Error fetching user roles"}, 500

        roles_data = roles_response.json()
        logger.debug("Guardian roles response data: %s", roles_data)

        # Handle both response formats for roles
        if isinstance(roles_data, list):
            user_roles = roles_data
        elif isinstance(roles_data, dict) and "roles" in roles_data:
            user_roles = roles_data.get("roles", [])
        else:
            logger.warning(
                "Unexpected roles response format from Guardian: %s",
                roles_data,
            )
            user_roles = []

        # Step 2: Fetch policies for each role
        all_policies = []
        seen_policy_ids = set()

        for user_role in user_roles:
            role_id = user_role.get("role_id")
            if not role_id:
                logger.warning("user_role missing role_id: %s", user_role)
                continue

            try:
                policies_response = requests.get(
                    f"{guardian_url}/roles/{role_id}/policies",
                    headers=headers,
                    timeout=5,
                )
            except requests.exceptions.RequestException as e:
                logger.error(
                    "Error contacting Guardian service for policies of role %s: %s",
                    role_id,
                    str(e),
                )
                # Continue with other roles instead of failing completely
                continue

            if policies_response.status_code == 404:
                logger.warning(
                    "Role %s not found in Guardian, skipping", role_id
                )
                continue

            if policies_response.status_code != 200:
                logger.error(
                    "Error fetching policies for role %s from Guardian: %s",
                    role_id,
                    policies_response.text,
                )
                # Continue with other roles
                continue

            policies_data = policies_response.json()
            logger.debug(
                "Guardian policies response for role %s: %s",
                role_id,
                policies_data,
            )

            # Handle response format (expecting a list of policies)
            if isinstance(policies_data, list):
                policies = policies_data
            elif (
                isinstance(policies_data, dict) and "policies" in policies_data
            ):
                policies = policies_data.get("policies", [])
            else:
                logger.warning(
                    "Unexpected policies response format for role %s: %s",
                    role_id,
                    policies_data,
                )
                policies = []

            # Deduplicate policies by ID
            for policy in policies:
                policy_id = policy.get("id")
                if policy_id and policy_id not in seen_policy_ids:
                    seen_policy_ids.add(policy_id)
                    all_policies.append(policy)

        logger.info(
            "Successfully fetched %d unique policies for user %s",
            len(all_policies),
            user_id,
        )
        return {"policies": all_policies}, 200
