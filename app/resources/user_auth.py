"""
module: app.resources.user_auth

This module defines Flask-RESTful resources for user authentication
operations in the Identity Service API.

It provides endpoints for verifying user passwords and other authentication
related operations.
"""

from datetime import datetime, timezone

from flask import request
from flask_restful import Resource
from sqlalchemy.exc import SQLAlchemyError

from app.logger import logger
from app.models import db
from app.models.user import User
from app.schemas.user_schema import UserSchema


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

        # Update last_login_at on successful authentication
        try:
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info("Updated last_login_at for user %s", email)
        except SQLAlchemyError as e:
            logger.error(
                "Error updating last_login_at for user %s: %s", email, str(e)
            )
            db.session.rollback()
            # Continue even if update fails - don't block authentication

        schema = UserSchema()
        return schema.dump(user), 200
