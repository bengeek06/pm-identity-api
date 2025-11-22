"""
Module: app.resources.user_password

This module defines Flask-RESTful resources for password management operations.
Implements admin-initiated password reset (Phase 1) with optional email-based
self-service reset (Phase 2).
"""

import secrets
import string
from datetime import datetime, timezone

from flask import g, request
from flask_restful import Resource
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.logger import logger
from app.models import db
from app.models.user import User
from app.utils import check_access_required, require_jwt_auth


def generate_temporary_password(length=12):
    """
    Generate a secure temporary password.

    Args:
        length (int): Length of the password (default: 12)

    Returns:
        str: Randomly generated password
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


class AdminPasswordResetResource(Resource):
    """
    Resource for admin-initiated password reset.

    Phase 1: Admin generates temporary password for user.
    User must change password on next login.
    """

    @require_jwt_auth()
    @check_access_required("update")
    def post(self, user_id):
        """
        Admin-initiated password reset (Issue #12 Phase 1).

        Generates a temporary password for the specified user and marks them
        as requiring a password change on next login.

        Args:
            user_id (str): The ID of the user whose password to reset

        Returns:
            tuple: JSON with temporary password and HTTP status code 200 on success
            tuple: Error message and HTTP status code 400, 403, 404 on failure
        """
        logger.info("Admin password reset requested for user ID %s", user_id)

        # Verify the user exists
        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        # Verify same company (multi-tenant isolation)
        jwt_data = getattr(g, "jwt_data", {})
        admin_company_id = jwt_data.get("company_id")

        if user.company_id != admin_company_id:
            logger.warning(
                "Admin from company %s attempted to reset password for user "
                "in company %s",
                admin_company_id,
                user.company_id,
            )
            return {
                "message": "Cannot reset password for user in different company"
            }, 403

        # Generate temporary password
        temp_password = generate_temporary_password()

        # Update user
        user.hashed_password = generate_password_hash(temp_password)
        user.password_reset_required = True
        user.last_password_change = datetime.now(timezone.utc)

        try:
            db.session.commit()
            logger.info(
                "Password reset successful for user %s by admin %s",
                user_id,
                jwt_data.get("user_id"),
            )

            return {
                "message": "Password reset successful",
                "temporary_password": temp_password,
                "password_reset_required": True,
                "note": "User must change password on next login. "
                "This is the only time the temporary password will be shown.",
            }, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                "Error resetting password for user %s: %s", user_id, str(e)
            )
            return {"message": "Error resetting password"}, 500


class UserChangePasswordResource(Resource):
    """
    Resource for user-initiated password change.

    Allows users to change their own password, required after admin reset.
    """

    @require_jwt_auth()
    def patch(self):
        """
        User changes their own password.

        Expected JSON:
        {
            "current_password": "old_password",
            "new_password": "new_password"
        }

        Returns:
            tuple: Success message and HTTP status code 200
            tuple: Error message and HTTP status code 400, 401 on failure
        """
        logger.info("Password change request")

        jwt_data = getattr(g, "jwt_data", {})
        user_id = jwt_data.get("user_id")

        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        json_data = request.get_json()
        if not json_data:
            return {"message": "No input data provided"}, 400

        current_password = json_data.get("current_password")
        new_password = json_data.get("new_password")

        if not current_password or not new_password:
            return {
                "message": "current_password and new_password are required"
            }, 400

        # Verify current password
        if not check_password_hash(user.hashed_password, current_password):
            logger.warning("Invalid current password for user %s", user_id)
            return {"message": "Current password is incorrect"}, 400

        # Validate new password (basic validation)
        if len(new_password) < 8:
            return {
                "message": "New password must be at least 8 characters"
            }, 400

        # Update password
        user.hashed_password = generate_password_hash(new_password)
        user.password_reset_required = False
        user.last_password_change = datetime.now(timezone.utc)

        try:
            db.session.commit()
            logger.info("Password changed successfully for user %s", user_id)

            return {
                "message": "Password changed successfully",
                "password_reset_required": False,
            }, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                "Error changing password for user %s: %s", user_id, str(e)
            )
            return {"message": "Error changing password"}, 500
