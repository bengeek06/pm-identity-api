# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
config.py
---------

This module defines the ConfigResource for exposing the current application
configuration through a REST endpoint.
"""

import os

from flask import current_app
from flask_restful import Resource

from app.utils import check_access_required, require_jwt_auth


class ConfigResource(Resource):
    """
    Resource for providing the application configuration.

    Methods:
        get():
            Retrieve the current application configuration.
    """

    @require_jwt_auth()
    @check_access_required("READ")
    def get(self):
        """
        Retrieve the current application configuration.

        Returns the actual Flask configuration values (processed and validated)
        rather than raw environment variables. This ensures the returned values
        match what the application is actually using.

        Returns:
            dict: A dictionary containing the application configuration and
            HTTP status code 200.
        """
        app_config = current_app.config

        # Read sensitive flags from environment for security
        jwt_secret_is_set = os.getenv("JWT_SECRET") is not None
        internal_auth_token_is_set = (
            os.getenv("INTERNAL_AUTH_TOKEN") is not None
        )

        config = {
            "FLASK_ENV": app_config.get("FLASK_ENV"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL"),  # Not in Flask config
            "DATABASE_URL": app_config.get("SQLALCHEMY_DATABASE_URI"),
            "JWT_SECRET_SET": jwt_secret_is_set,
            "INTERNAL_AUTH_TOKEN_SET": internal_auth_token_is_set,
            "USE_GUARDIAN_SERVICE": app_config.get("USE_GUARDIAN_SERVICE"),
            "GUARDIAN_SERVICE_URL": app_config.get("GUARDIAN_SERVICE_URL"),
            "GUARDIAN_SERVICE_TIMEOUT": app_config.get(
                "GUARDIAN_SERVICE_TIMEOUT"
            ),
            "USE_STORAGE_SERVICE": app_config.get("USE_STORAGE_SERVICE"),
            "STORAGE_SERVICE_URL": app_config.get("STORAGE_SERVICE_URL"),
            "STORAGE_REQUEST_TIMEOUT": app_config.get(
                "STORAGE_REQUEST_TIMEOUT"
            ),
            "MAX_AVATAR_SIZE_MB": app_config.get("MAX_AVATAR_SIZE_MB"),
            "USE_EMAIL_SERVICE": app_config.get("USE_EMAIL_SERVICE"),
            "MAIL_SERVER": app_config.get("MAIL_SERVER"),
            "MAIL_PORT": app_config.get("MAIL_PORT"),
            "MAIL_USE_TLS": app_config.get("MAIL_USE_TLS"),
            "MAIL_USE_SSL": app_config.get("MAIL_USE_SSL"),
            "MAIL_USERNAME": app_config.get("MAIL_USERNAME"),
            "MAIL_DEFAULT_SENDER": app_config.get("MAIL_DEFAULT_SENDER"),
            "MAIL_MAX_EMAILS": app_config.get("MAIL_MAX_EMAILS"),
            "RATELIMIT_STORAGE_URI": app_config.get("RATELIMIT_STORAGE_URI"),
            "RATELIMIT_STRATEGY": app_config.get("RATELIMIT_STRATEGY"),
            "PASSWORD_RESET_OTP_TTL_MINUTES": app_config.get(
                "PASSWORD_RESET_OTP_TTL_MINUTES"
            ),
            "PASSWORD_RESET_OTP_MAX_ATTEMPTS": app_config.get(
                "PASSWORD_RESET_OTP_MAX_ATTEMPTS"
            ),
        }
        return config, 200
