"""
module: app.resources.user_roles

This module defines Flask-RESTful resources for managing user role assignments
in the Identity Service API via the Guardian Service.

It provides endpoints for listing roles assigned to a user, adding new role
assignments, retrieving specific role assignments, and removing role assignments.
"""

import os

import requests
from flask import g, request
from flask_restful import Resource
from werkzeug.exceptions import BadRequest

from app.logger import logger
from app.models.user import User
from app.utils import check_access_required, require_jwt_auth


class UserRolesListResource(Resource):
    """
    Resource for handling roles by users.

    Methods:
        get(user_id):
            Retrieve all roles for a specific user.
        post(user_id):
            Add a new role for a specific user.
    """

    @staticmethod
    def _validate_user_access(user_id, company_id):
        """
        Validate that the target user exists and belongs to the same company.

        Args:
            user_id (str): The ID of the user to validate.
            company_id (str): The company ID from JWT.

        Returns:
            tuple: (User, error_response)
                - If valid: (User, None)
                - If invalid: (None, (dict, int))
        """
        target_user = User.get_by_id(user_id)
        if not target_user:
            logger.warning("User with ID %s not found", user_id)
            return None, ({"message": "User not found"}, 404)

        if target_user.company_id != company_id:
            logger.warning(
                "Attempted to access user %s from different company", user_id
            )
            return None, ({"message": "Access denied"}, 403)

        return target_user, None

    @staticmethod
    def _extract_role_id(json_data):
        """
        Extract and validate role_id from request JSON.

        Args:
            json_data (dict): The JSON data from the request.

        Returns:
            tuple: (role_id, error_response)
                - If valid: (str, None)
                - If invalid: (None, (dict, int))
        """
        if not json_data:
            logger.error("No JSON data provided")
            return None, ({"message": "JSON data required"}, 400)

        # Accept either 'role' (for backward compatibility) or 'role_id'
        role_id = json_data.get("role_id") or json_data.get("role")
        if not role_id:
            logger.error("Role ID field missing in request")
            return None, ({"message": "Role ID field is required"}, 400)

        if not isinstance(role_id, str) or not role_id.strip():
            logger.error("Invalid role ID format: %s", role_id)
            return None, (
                {"message": "Role ID must be a non-empty string"},
                400,
            )

        return role_id.strip(), None

    @staticmethod
    def _handle_guardian_response(response, role_id, user_id):
        """
        Handle the Guardian service response for role assignment.

        Args:
            response: The response from Guardian service.
            role_id (str): The role ID being assigned.
            user_id (str): The user ID receiving the role.

        Returns:
            tuple: (dict, int) - Response data and status code
        """
        if response.status_code == 409:
            logger.warning(
                "Role ID %s already assigned to user %s", role_id, user_id
            )
            return {
                "message": f"Role '{role_id}' already assigned to user"
            }, 409
        if response.status_code == 400:
            logger.error("Bad request to Guardian: %s", response.text)
            return {"message": "Invalid role or request data"}, 400
        if response.status_code != 201:
            logger.error("Error assigning role in Guardian: %s", response.text)
            return {"message": "Error assigning role"}, 500

        logger.info(
            "Successfully assigned role ID %s to user %s", role_id, user_id
        )
        return response.json(), 201

    @require_jwt_auth()
    @check_access_required("list")
    def get(self, user_id):
        """
        Get all roles for a specific user.

        Args:
            user_id (str): The ID of the user whose roles to retrieve.

        Returns:
            tuple: List of roles and HTTP status code 200.
        """
        logger.info("Fetching roles for user ID %s", user_id)

        jwt_data = getattr(g, "jwt_data", {})
        requesting_user_id = jwt_data.get("user_id")
        company_id = jwt_data.get("company_id")

        if not requesting_user_id:
            logger.error("user_id missing in JWT")
            return {"message": "user_id missing in JWT"}, 400

        # Verify that the requested user belongs to the same company
        target_user = User.get_by_id(user_id)
        if not target_user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        if target_user.company_id != company_id:
            logger.warning(
                "User %s attempted to access roles for user %s from different company",
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

        try:
            # Add a timeout to avoid hanging indefinitely and handle network errors
            response = requests.get(
                f"{guardian_url}/user-roles",
                params={"user_id": user_id},
                headers=headers,
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            logger.error("Error contacting Guardian service: %s", str(e))
            return {"message": "Error fetching roles"}, 500
        if response.status_code != 200:
            logger.error(
                "Error fetching roles from Guardian: %s", response.text
            )
            return {"message": "Error fetching roles"}, 500

        response_data = response.json()
        logger.debug("Guardian response data: %s", response_data)

        # Handle both response formats:
        # - Direct list: [{"id": "role1", ...}, {"id": "role2", ...}]
        # - Object with roles key: {"roles": [{"id": "role1", ...}, ...]}
        # - Other formats: Default to empty list with warning
        if isinstance(response_data, list):
            roles = response_data
        elif isinstance(response_data, dict) and "roles" in response_data:
            roles = response_data.get("roles", [])
        else:
            logger.warning(
                "Unexpected response format from Guardian, defaulting to empty roles: %s",
                response_data,
            )
            roles = []

        return {"roles": roles}, 200

    @require_jwt_auth()
    @check_access_required("create")
    def post(self, user_id):
        """
        Add a role to a specific user.

        Expects:
            JSON payload with 'role' field containing the role to assign.

        Args:
            user_id (str): The ID of the user to assign the role to.

        Returns:
            tuple: Success message and HTTP status code 201 on success.
            tuple: Error message and HTTP status code 400, 403, 404, or 500 on failure.
        """
        logger.info("Adding role for user ID %s", user_id)

        jwt_data = getattr(g, "jwt_data", {})
        requesting_user_id = jwt_data.get("user_id")
        company_id = jwt_data.get("company_id")

        if not requesting_user_id:
            logger.error("user_id missing in JWT")
            return {"message": "user_id missing in JWT"}, 400

        # Verify that the requested user belongs to the same company
        _, error = self._validate_user_access(user_id, company_id)
        if error:
            return error

        try:
            json_data = request.get_json(force=True)
        except BadRequest:
            json_data = None

        # Extract and validate role_id
        role_id, error = self._extract_role_id(json_data)
        if error:
            return error

        guardian_url = os.environ.get("GUARDIAN_SERVICE_URL")
        if not guardian_url:
            logger.error("GUARDIAN_SERVICE_URL not set")
            return {"message": "Internal server error"}, 500

        # Get JWT token from cookies to forward to Guardian service
        jwt_token = request.cookies.get("access_token")
        headers = {}
        if jwt_token:
            headers["Cookie"] = f"access_token={jwt_token}"

        try:
            # Send POST request to Guardian service to assign role
            response = requests.post(
                f"{guardian_url}/user-roles",
                json={"user_id": user_id, "role_id": role_id},
                headers=headers,
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            logger.error("Error contacting Guardian service: %s", str(e))
            return {"message": "Error assigning role"}, 500

        return self._handle_guardian_response(response, role_id, user_id)


class UserRolesResource(Resource):
    """
    Resource for handling a specific role assignment for a user.

    Methods:
        get():
            Retrieve a specific role assignment for a user.
        delete():
            Remove a specific role assignment from a user.
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, user_id, user_role_id):
        """
        Get a specific role assignment for a user.

        Args:
            user_id (str): The ID of the user whose role to retrieve.
            user_role_id (str): The ID of the specific role assignment.
        Returns:
            tuple: Role assignment information and HTTP status code 200 on success.
        """
        logger.info(
            "Retrieving role assignment %s for user %s", user_role_id, user_id
        )

        # Get company_id from JWT data stored in g by the decorator
        jwt_data = getattr(g, "jwt_data", {})
        company_id = jwt_data.get("company_id")

        if not company_id:
            logger.error("company_id missing in JWT")
            return {"message": "Authentication error"}, 401

        # Check if user exists and belongs to the same company
        user = User.query.filter_by(id=user_id, company_id=company_id).first()
        if not user:
            logger.warning(
                "User %s not found or access denied for company %s",
                user_id,
                company_id,
            )
            return {"message": "User not found or access denied"}, 404

        guardian_url = os.environ.get("GUARDIAN_SERVICE_URL")
        if not guardian_url:
            logger.error("GUARDIAN_SERVICE_URL not set")
            return {"message": "Internal server error"}, 500

        # Get JWT token from cookies to forward to Guardian service
        jwt_token = request.cookies.get("access_token")
        headers = {}
        if jwt_token:
            headers["Cookie"] = f"access_token={jwt_token}"

        try:
            # Get specific role assignment from Guardian service
            response = requests.get(
                f"{guardian_url}/user-roles/{user_role_id}",
                headers=headers,
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            logger.error("Error contacting Guardian service: %s", str(e))
            return {"message": "Error retrieving role"}, 500

        if response.status_code == 404:
            logger.warning("Role assignment %s not found", user_role_id)
            return {"message": "Role assignment not found"}, 404
        if response.status_code != 200:
            logger.error(
                "Error retrieving role from Guardian: %s", response.text
            )
            return {"message": "Error retrieving role"}, 500

        role_data = response.json()

        # Verify that the role assignment belongs to the requested user
        if role_data.get("user_id") != user_id:
            logger.warning(
                "Role assignment %s does not belong to user %s",
                user_role_id,
                user_id,
            )
            return {"message": "Role assignment not found"}, 404

        logger.info(
            "Successfully retrieved role assignment %s for user %s",
            user_role_id,
            user_id,
        )
        return role_data, 200

    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, user_id, user_role_id):
        """
        Delete a specific role assignment from a user.

        Args:
            user_id (str): The ID of the user whose role to remove.
            user_role_id (str): The ID of the specific role assignment to remove.
        Returns:
            tuple: Empty response and HTTP status code 204 on success.
        """
        logger.info(
            "Removing role assignment %s from user %s", user_role_id, user_id
        )

        # Get company_id from JWT data stored in g by the decorator
        jwt_data = getattr(g, "jwt_data", {})
        company_id = jwt_data.get("company_id")

        if not company_id:
            logger.error("company_id missing in JWT")
            return {"message": "Authentication error"}, 401

        # Check if user exists and belongs to the same company
        user = User.query.filter_by(id=user_id, company_id=company_id).first()
        if not user:
            logger.warning(
                "User %s not found or access denied for company %s",
                user_id,
                company_id,
            )
            return {"message": "User not found or access denied"}, 404

        guardian_url = os.environ.get("GUARDIAN_SERVICE_URL")
        if not guardian_url:
            logger.error("GUARDIAN_SERVICE_URL not set")
            return {"message": "Internal server error"}, 500

        # Get JWT token from cookies to forward to Guardian service
        jwt_token = request.cookies.get("access_token")
        headers = {}
        if jwt_token:
            headers["Cookie"] = f"access_token={jwt_token}"

        try:
            # First, verify the role assignment exists and belongs to this user
            get_response = requests.get(
                f"{guardian_url}/user-roles/{user_role_id}",
                headers=headers,
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            logger.error("Error contacting Guardian service: %s", str(e))
            return {"message": "Error removing role"}, 500

        if get_response.status_code == 404:
            logger.warning("Role assignment %s not found", user_role_id)
            return {"message": "Role assignment not found"}, 404
        if get_response.status_code != 200:
            logger.error(
                "Error checking role in Guardian: %s", get_response.text
            )
            return {"message": "Error removing role"}, 500

        role_data = get_response.json()

        # Verify that the role assignment belongs to the requested user
        if role_data.get("user_id") != user_id:
            logger.warning(
                "Role assignment %s does not belong to user %s",
                user_role_id,
                user_id,
            )
            return {"message": "Role assignment not found"}, 404

        try:
            # Delete the role assignment from Guardian service
            response = requests.delete(
                f"{guardian_url}/user-roles/{user_role_id}",
                headers=headers,
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            logger.error("Error contacting Guardian service: %s", str(e))
            return {"message": "Error removing role"}, 500

        if response.status_code == 404:
            logger.warning(
                "Role assignment %s not found for deletion", user_role_id
            )
            return {"message": "Role assignment not found"}, 404
        if response.status_code not in [204, 200]:
            logger.error(
                "Error removing role from Guardian: %s", response.text
            )
            return {"message": "Error removing role"}, 500

        logger.info(
            "Successfully removed role assignment %s from user %s",
            user_role_id,
            user_id,
        )
        return {}, 204
