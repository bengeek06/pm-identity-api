"""
module: app.resources.user

This module defines the Flask-RESTful resources for basic User CRUD operations
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting users. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.

For related user operations, see:
- app.resources.user_position: Users by position
- app.resources.user_roles: User role assignments (RBAC)
- app.resources.user_policies: User policy aggregation (RBAC)
- app.resources.user_permissions: User permission aggregation (RBAC)
- app.resources.user_auth: User authentication operations
"""

import os

from flask import request, g

from marshmallow import ValidationError

from werkzeug.security import generate_password_hash

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from flask_restful import Resource

import jwt

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

    @require_jwt_auth()
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

    @require_jwt_auth()
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

    @require_jwt_auth()
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

    @require_jwt_auth()
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

    @require_jwt_auth()
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

    @require_jwt_auth()
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
