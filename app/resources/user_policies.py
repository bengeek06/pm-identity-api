"""
module: app.resources.user_policies

This module defines Flask-RESTful resources for aggregating policies
associated with users via the Guardian Service.

It provides endpoints for retrieving all policies assigned to a user
through their role assignments.
"""

from flask import current_app
from flask_restful import Resource

from app.logger import logger
from app.resources.guardian_helpers import (
    fetch_policies_for_roles,
    fetch_user_roles,
    get_guardian_headers,
    validate_user_access,
)
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
    def get(self, user_id):
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

        # Validate user access
        error, status = validate_user_access(user_id)
        if error:
            return error, status

        # If Guardian Service is disabled, return empty policies
        if not current_app.config.get("USE_GUARDIAN_SERVICE"):
            logger.debug(
                "Guardian Service is disabled - returning empty policies list"
            )
            return {"policies": []}, 200

        guardian_url = current_app.config["GUARDIAN_SERVICE_URL"]
        headers = get_guardian_headers()

        # Step 1: Fetch all roles for the user
        user_roles, error = fetch_user_roles(user_id, guardian_url, headers)
        if error:
            return error

        # Step 2: Fetch policies for each role and deduplicate
        _, all_policies = fetch_policies_for_roles(
            user_roles, guardian_url, headers
        )

        logger.info(
            "Successfully fetched %d unique policies for user %s",
            len(all_policies),
            user_id,
        )
        return {"policies": all_policies}, 200
