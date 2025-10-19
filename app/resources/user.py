"""
module: app.resources.user

This module defines the Flask-RESTful resources for managing User entities
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting users, as well as for managing users by company or
position, and for verifying user passwords. The resources use Marshmallow
schemas for validation and serialization, and handle database errors
gracefully.
"""

import os
from flask import request, g
from marshmallow import ValidationError
from werkzeug.exceptions import BadRequest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import generate_password_hash
from flask_restful import Resource

import jwt
import requests

from app.models import db
from app.logger import logger
from app.utils import require_jwt_auth, check_access_required
from app.models.user import User
from app.schemas.user_schema import UserSchema
from app.models.company import Company


class UserListResource(Resource):
    """
    Resource for handling user list operations.

    Methods:
        get():
            Retrieve all users from the database.

        post():
            Create a new user with the provided data.
    """

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("list")
    def get(self):
        """
        Get all users from the authenticated user's company.

        Returns:
            tuple: List of serialized users and HTTP status code 200.
        """
        logger.info("Fetching all users")
        try:
            # Get company_id from JWT data stored in g by the decorator
            jwt_data = getattr(g, "jwt_data", {})
            company_id = jwt_data.get("company_id")

            if not company_id:
                logger.error("company_id missing in JWT")
                return {"message": "company_id missing in JWT"}, 400

            # Filter users by company_id to only return users from the same company
            users = User.query.filter_by(company_id=company_id).all()
            schema = UserSchema(many=True)
            return schema.dump(users), 200
        except SQLAlchemyError as e:
            logger.error("Error fetching users: %s", str(e))
            return {"message": "Error fetching users"}, 500

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("create")
    def post(self):
        """
        Create a new user.

        Expects:
            JSON payload with at least 'email', 'password', 'first_name',
            'last_name', and 'company_id'.

        Returns:
            tuple: The serialized created user and HTTP status code 201 on
                   success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new user")

        jwt_token = request.cookies.get("access_token")
        if not jwt_token:
            logger.error("Missing JWT token")
            return {"message": "Missing JWT token"}, 401

        logger.debug("Found JWT token in cookies")
        jwt_secret = os.environ.get("JWT_SECRET")
        if not jwt_secret:
            logger.warning("JWT_SECRET not found in environment variables.")
        try:
            payload = jwt.decode(jwt_token, jwt_secret, algorithms=["HS256"])
            company_id = payload.get("company_id")
            if not company_id:
                logger.error("company_id missing in JWT")
                return {"message": "company_id missing in JWT"}, 400
            logger.debug(f"Extracted company_id {company_id} from JWT")
        except jwt.ExpiredSignatureError:
            logger.error("JWT expired")
            return {"message": "JWT expired"}, 401
        except jwt.InvalidTokenError as e:
            logger.error("JWT error: %s", str(e))
            return {"message": "JWT error"}, 401

        json_data = request.get_json()
        json_data["company_id"] = company_id

        user_schema = UserSchema(session=db.session)

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            user = user_schema.load(json_data)
            # Handle nullable company_id for superuser creation
            if (
                "company_id" in json_data
                and json_data["company_id"] is not None
            ):
                company = Company.get_by_id(json_data["company_id"])
                if not company:
                    logger.warning(
                        "Company with ID %s not found", json_data["company_id"]
                    )
                    return {"message": "Company not found"}, 404
                user.company = company
            # If company_id is None, this is a superuser creation
            db.session.add(user)
            db.session.commit()
            return user_schema.dump(user), 201
        except ValidationError as e:
            logger.error("Validation error: %s", e.messages)
            return {"message": "Validation error", "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e.orig))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500


class UserResource(Resource):
    """
    Resource for handling individual user operations.

    Methods:
        get(user_id):
            Retrieve a user by ID.

        put(user_id):
            Update a user by ID.

        patch(user_id):
            Partially update a user by ID.

        delete(user_id):
            Delete a user by ID.
    """

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("read")
    def get(self, user_id):
        """
        Get a user by ID.

        Args:
            user_id (str): The ID of the user to retrieve.

        Returns:
            tuple: The serialized user and HTTP status code 200 on success.
                   HTTP status code 404 if the user is not found.
        """
        logger.info("Fetching user with ID %s", user_id)

        user = User.get_by_id(user_id)
        if not user:
            return {"message": "User not found"}, 404

        schema = UserSchema()
        return schema.dump(user), 200

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("update")
    def put(self, user_id):
        """
        Update a user by ID.

        Expects:
            JSON payload with fields to update.

        Args:
            user_id (str): The ID of the user to update.

        Returns:
            tuple: The serialized updated user and HTTP status code 200 on
                   success.
                   HTTP status code 404 if the user is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info("Updating user with ID %s", user_id)

        json_data = request.get_json()
        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        user_schema = UserSchema(session=db.session, context={"user": user})

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            updated_user = user_schema.load(json_data, instance=user)
            db.session.commit()
            return user_schema.dump(updated_user), 200
        except ValidationError as e:
            logger.error("Validation error: %s", e.messages)
            return {"message": "Validation error", "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e.orig))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("update")
    def patch(self, user_id):
        """
        Partially update a user by ID.

        Expects:
            JSON payload with fields to update.

        Args:
            user_id (str): The ID of the user to update.

        Returns:
            tuple: The serialized updated user and HTTP status code 200 on
                   success.
                   HTTP status code 404 if the user is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info("Partially updating user with ID %s", user_id)

        json_data = request.get_json()
        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        user_schema = UserSchema(
            session=db.session, partial=True, context={"user": user}
        )

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            # Company_id modification is prevented by schema validation
            updated_user = user_schema.load(
                json_data, instance=user, partial=True
            )
            db.session.commit()
            return user_schema.dump(updated_user), 200
        except ValidationError as e:
            logger.error("Validation error: %s", e.messages)
            return {"message": "Validation error", "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e.orig))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("delete")
    def delete(self, user_id):
        """
        Delete a user by ID.

        Args:
            user_id (str): The ID of the user to delete.

        Returns:
            tuple: Message and HTTP status code 204 on success,
                   or error message and code on failure.
        """
        logger.info("Deleting user with ID %s", user_id)

        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        try:
            db.session.delete(user)
            db.session.commit()
            return {"message": "User deleted successfully"}, 204
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500


class UserPositionResource(Resource):
    """
    Resource for handling users by position.

    Methods:
        get(position_id):
            Retrieve all users for a specific position.
    """

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("read")
    def get(self, position_id):
        """
        Get all users for a specific position.

        Args:
            position_id (str): The ID of the position.

        Returns:
            tuple: List of serialized users and HTTP status code 200.
        """
        logger.info("Fetching users for position ID %s", position_id)

        try:
            users = User.get_by_position_id(position_id)
            schema = UserSchema(many=True)
            return schema.dump(users), 200
        except SQLAlchemyError as e:
            logger.error(
                "Error fetching users for position %s: %s", position_id, str(e)
            )
            return {"message": "Error fetching users"}, 500


class UserRolesListResource(Resource):
    """
    Resource for handling roles by users.

    Methods:
        get(user_id):
            Retrieve all roles for a specific user.
        post(user_id):
            Add a new role for a specific user.
    """

    @require_jwt_auth(extract_company_id=True)
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

    @require_jwt_auth(extract_company_id=True)
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
        target_user = User.get_by_id(user_id)
        if not target_user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        if target_user.company_id != company_id:
            logger.warning(
                "User %s attempted to assign role for user %s from different company",
                requesting_user_id,
                user_id,
            )
            return {"message": "Access denied"}, 403

        try:
            json_data = request.get_json(force=True)
        except BadRequest:
            json_data = None

        if not json_data:
            logger.error("No JSON data provided")
            return {"message": "JSON data required"}, 400

        # Accept either 'role' (for backward compatibility) or 'role_id'
        role_id = json_data.get("role_id") or json_data.get("role")
        if not role_id:
            logger.error("Role ID field missing in request")
            return {"message": "Role ID field is required"}, 400

        if not isinstance(role_id, str) or not role_id.strip():
            logger.error("Invalid role ID format: %s", role_id)
            return {"message": "Role ID must be a non-empty string"}, 400

        role_id = role_id.strip()

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

        if response.status_code == 409:
            # Role already exists for this user
            logger.warning(
                "Role ID %s already assigned to user %s", role_id, user_id
            )
            return {
                "message": f"Role '{role_id}' already assigned to user"
            }, 409
        elif response.status_code == 400:
            # Bad request from Guardian (invalid role, etc.)
            logger.error("Bad request to Guardian: %s", response.text)
            return {"message": "Invalid role or request data"}, 400
        elif response.status_code != 201:
            logger.error("Error assigning role in Guardian: %s", response.text)
            return {"message": "Error assigning role"}, 500

        logger.info(
            "Successfully assigned role ID %s to user %s", role_id, user_id
        )
        return response.json(), 201


class UserRolesResource(Resource):
    """
    Resource for handling a specific role assignment for a user.

    Methods:
        get():
            Retrieve a specific role assignment for a user.
        delete():
            Remove a specific role assignment from a user.
    """

    @require_jwt_auth(extract_company_id=True)
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
        elif response.status_code != 200:
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

    @require_jwt_auth(extract_company_id=True)
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
        elif get_response.status_code != 200:
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
        elif response.status_code not in [204, 200]:
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


class VerifyPasswordResource(Resource):
    """
    Resource for verifying user passwords.

    Methods:
        post():
            Verify a user's password.
    """

    def post(self):
        """
        Verify a user's password.

        Expects:
            JSON payload with 'email' and 'password'.

        Returns:
            tuple: The serialized user and HTTP status code 200 if credentials
                   are valid.
            tuple: Error message and HTTP status code 400 or 403 on failure.
        """
        json_data = request.get_json()
        email = json_data.get("email")

        if not email:
            logger.error("Email is required for verification")
            return {"message": "Email is required"}, 400

        logger.info("Verifying password for user %s", email)

        password = json_data.get("password")

        if not password:
            logger.error("Password is required for verification")
            return {"message": "Password is required"}, 400

        user = User.get_by_email(email)
        if not user or not user.verify_password(password):
            logger.warning("Invalid user or password for email %s", email)
            return {"message": "User or password invalid"}, 403

        schema = UserSchema()
        return schema.dump(user), 200
