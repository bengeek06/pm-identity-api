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

from flask import request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_restful import Resource
from werkzeug.security import generate_password_hash

from app.models import db
from app.logger import logger
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
    def get(self):
        """
        Get all users.

        Returns:
            tuple: List of serialized users and HTTP status code 200.
        """
        logger.info("Fetching all users")
        try:
            users = User.query.all()
            schema = UserSchema(many=True)
            return schema.dump(users), 200
        except SQLAlchemyError as e:
            logger.error("Error fetching users: %s", str(e))
            return {"message": "Error fetching users"}, 500

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

        json_data = request.get_json()
        user_schema = UserSchema(session=db.session)

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            user = user_schema.load(json_data)
            if "company_id" in json_data:
                company = Company.get_by_id(json_data["company_id"])
                if not company:
                    logger.warning(
                        "Company with ID %s not found",
                        json_data["company_id"]
                    )
                    return {"message": "Company not found"}, 404
                user.company = company
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
        user_schema = UserSchema(session=db.session)

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            user = User.get_by_id(user_id)
            if not user:
                logger.warning("User with ID %s not found", user_id)
                return {"message": "User not found"}, 404

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
        user_schema = UserSchema(session=db.session, partial=True)

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            user = User.get_by_id(user_id)
            if not user:
                logger.warning("User with ID %s not found", user_id)
                return {"message": "User not found"}, 404

            updated_user = user_schema.load(
                json_data, instance=user, partial=True)
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


class UserCompanyResource(Resource):
    """
    Resource for handling users by company.

    Methods:
        get(company_id):
            Retrieve all users for a specific company.

        post(company_id):
            Create a new user for a specific company.

        delete(company_id):
            Delete all users for a specific company.
    """
    def get(self, company_id):
        """
        Get all users for a specific company.

        Args:
            company_id (str): The ID of the company.

        Returns:
            tuple: List of serialized users and HTTP status code 200.
        """
        logger.info("Fetching users for company ID %s", company_id)

        try:
            users = User.get_by_company_id(company_id)
            schema = UserSchema(many=True)
            return schema.dump(users), 200
        except SQLAlchemyError as e:
            logger.error(
                "Error fetching users for company %s: %s", company_id, str(e))
            return {"message": "Error fetching users"}, 500

    def post(self, company_id):
        """
        Create a new user for a specific company.

        Expects:
            JSON payload with at least 'email', 'password', 'first_name',
            and 'last_name'.

        Args:
            company_id (str): The ID of the company.

        Returns:
            tuple: The serialized created user and HTTP status code 201 on
                   success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new user for company ID %s", company_id)

        company = Company.get_by_id(company_id)
        if not company:
            logger.warning("Company with ID %s not found", company_id)
            return {"message": "Company not found"}, 404

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

    def delete(self, company_id):
        """
        Delete all users for a specific company.

        Args:
            company_id (str): The ID of the company.

        Returns:
            tuple: Message and HTTP status code 204 on success,
                   or error message and code on failure.
        """
        logger.info("Deleting all users for company ID %s", company_id)

        try:
            users = User.get_by_company_id(company_id)
            if not users:
                return {"message": "No users found for this company"}, 404

            for user in users:
                db.session.delete(user)
            db.session.commit()
            return {"message": "All users deleted successfully"}, 204
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
                "Error fetching users for position %s: %s",
                position_id, str(e)
            )
            return {"message": "Error fetching users"}, 500


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
