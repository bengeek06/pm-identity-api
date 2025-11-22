"""
Module: app.resources.password_reset

This module defines Flask-RESTful resources for email-based password reset
with OTP verification (Issue #12 Phase 2).

Security features:
- Rate limiting per IP and per email
- Always returns 200 OK (never reveals email existence)
- OTP expiration (15 minutes default)
- Maximum 3 verification attempts
- Hashed OTP storage
"""

import secrets
from datetime import datetime, timezone

from flask import current_app, request
from flask_restful import Resource
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.email_helper import send_password_reset_email
from app.logger import logger
from app.models import db
from app.models.password_reset_otp import PasswordResetOTP
from app.models.user import User

# Constants to avoid duplication
MSG_RESET_SENT = "If the email exists, a password reset code has been sent."
MSG_INVALID_OTP = "Invalid email or OTP code"


def generate_otp_code(length=6):
    """
    Generate a secure numeric OTP code.

    Args:
        length (int): Number of digits (default: 6)

    Returns:
        str: Randomly generated numeric code
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


class PasswordResetRequestResource(Resource):
    """
    Resource for requesting password reset via email.

    Public endpoint - rate limiting applied in routes.py.
    """

    def post(self):
        """
        Request password reset OTP via email (Issue #12 Phase 2).

        Expected JSON:
        {
            "email": "user@example.com"
        }

        Security:
        - ALWAYS returns 200 OK (never reveals email existence)
        - Rate limited per IP (3 per 15min) - applied in routes.py
        - Rate limited per email (5 per day) - applied in routes.py

        Returns:
            tuple: Generic success message and HTTP status code 200
        """
        client_ip = request.remote_addr
        logger.info("Password reset request from IP %s", client_ip)

        json_data = request.get_json(silent=True)
        if not json_data:
            # Return 200 even for bad requests (security)
            return {"message": MSG_RESET_SENT}, 200

        email = json_data.get("email", "").strip().lower()

        if not email:
            # Return 200 even for missing email (security)
            return {"message": MSG_RESET_SENT}, 200

        # Find user (but don't reveal if exists)
        user = User.query.filter_by(email=email).first()

        if user:
            # Check if email service is enabled
            if not current_app.config.get("USE_EMAIL_SERVICE", False):
                logger.warning(
                    "Password reset requested but email service is disabled"
                )
                # Still return 200 (don't reveal configuration)
                return {"message": MSG_RESET_SENT}, 200

            # Generate OTP
            otp_code = generate_otp_code(6)
            otp_hash = generate_password_hash(otp_code)

            # Invalidate previous OTPs
            PasswordResetOTP.invalidate_all_for_user(user.id)

            # Create new OTP
            ttl_minutes = current_app.config.get(
                "PASSWORD_RESET_OTP_TTL_MINUTES", 15
            )
            PasswordResetOTP.create_otp(user.id, otp_hash, ttl_minutes)

            try:
                db.session.commit()

                # Send email
                email_sent = send_password_reset_email(
                    email, otp_code, user.first_name
                )

                if email_sent:
                    logger.info(
                        "Password reset OTP sent to %s (user ID %s)",
                        email,
                        user.id,
                    )
                else:
                    logger.error(
                        "Failed to send password reset email to %s", email
                    )

            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(
                    "Error creating password reset OTP for %s: %s",
                    email,
                    str(e),
                )

        else:
            logger.info(
                "Password reset requested for non-existent email: %s "
                "(IP: %s)",
                email,
                client_ip,
            )

        # ALWAYS return the same response (security)
        return {"message": MSG_RESET_SENT}, 200


class PasswordResetConfirmResource(Resource):
    """
    Resource for confirming password reset with OTP.

    Public endpoint - rate limiting applied in routes.py.
    """

    def post(self):
        """
        Confirm password reset with OTP and set new password.

        Expected JSON:
        {
            "email": "user@example.com",
            "otp_code": "123456",
            "new_password": "new_secure_password"
        }

        Returns:
            tuple: Success/error message and appropriate HTTP status code
        """
        client_ip = request.remote_addr
        logger.info("Password reset confirmation from IP %s", client_ip)

        json_data = request.get_json()
        if not json_data:
            return {"message": "No input data provided"}, 400

        email = json_data.get("email", "").strip().lower()
        otp_code = json_data.get("otp_code", "").strip()
        new_password = json_data.get("new_password")

        if not email or not otp_code or not new_password:
            return {
                "message": "email, otp_code, and new_password are required"
            }, 400

        # Validate password
        if len(new_password) < 8:
            return {
                "message": "New password must be at least 8 characters"
            }, 400

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            logger.warning(
                "Password reset confirmation for non-existent email: %s "
                "(IP: %s)",
                email,
                client_ip,
            )
            return {"message": MSG_INVALID_OTP}, 400

        # Get valid OTP
        otp_record = PasswordResetOTP.get_valid_otp(user.id)
        if not otp_record:
            logger.warning(
                "No valid OTP found for user %s (IP: %s)", user.id, client_ip
            )
            return {"message": MSG_INVALID_OTP}, 400

        # Check if OTP is still valid
        if not otp_record.is_valid():
            logger.warning(
                "Expired or invalid OTP for user %s (IP: %s)",
                user.id,
                client_ip,
            )
            return {"message": MSG_INVALID_OTP}, 400

        # Verify OTP code
        if not check_password_hash(otp_record.otp_code, otp_code):
            # Increment attempts
            otp_record.increment_attempts()

            max_attempts = current_app.config.get(
                "PASSWORD_RESET_OTP_MAX_ATTEMPTS", 3
            )

            if otp_record.attempts >= max_attempts:
                logger.warning(
                    "Max OTP attempts reached for user %s (IP: %s)",
                    user.id,
                    client_ip,
                )

            try:
                db.session.commit()
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(
                    "Error incrementing OTP attempts for user %s: %s",
                    user.id,
                    str(e),
                )

            return {"message": MSG_INVALID_OTP}, 400

        # OTP is valid - update password
        user.hashed_password = generate_password_hash(new_password)
        user.password_reset_required = False
        user.last_password_change = datetime.now(timezone.utc)

        # Mark OTP as used
        otp_record.mark_used()

        try:
            db.session.commit()
            logger.info(
                "Password reset successful for user %s (IP: %s)",
                user.id,
                client_ip,
            )

            return {
                "message": "Password reset successful. You can now log in "
                "with your new password."
            }, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                "Error resetting password for user %s: %s", user.id, str(e)
            )
            return {"message": "Error resetting password"}, 500
