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

        Returns:
            dict: A dictionary containing the application configuration and
            HTTP status code 200.
        """
        jwt_secret_is_set = os.getenv("JWT_SECRET") is not None
        internal_auth_token_is_set = (
            os.getenv("INTERNAL_AUTH_TOKEN") is not None
        )

        config = {
            "FLASK_ENV": os.getenv("FLASK_ENV"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL"),
            "DATABASE_URL": os.getenv("DATABASE_URL"),
            "JWT_SECRET_SET": jwt_secret_is_set,
            "INTERNAL_AUTH_TOKEN_SET": internal_auth_token_is_set,
            "USE_GUARDIAN_SERVICE": os.getenv("USE_GUARDIAN_SERVICE"),
            "GUARDIAN_SERVICE_URL": os.getenv("GUARDIAN_SERVICE_URL"),
            "GUARDIAN_SERVICE_TIMEOUT": os.getenv("GUARDIAN_SERVICE_TIMEOUT"),
            "USE_STORAGE_SERVICE": os.getenv("USE_STORAGE_SERVICE"),
            "STORAGE_SERVICE_URL": os.getenv("STORAGE_SERVICE_URL"),
            "STORAGE_REQUEST_TIMEOUT": os.getenv("STORAGE_REQUEST_TIMEOUT"),
            "MAX_AVATAR_SIZE_MB": os.getenv("MAX_AVATAR_SIZE_MB"),
            "USE_EMAIL_SERVICE": os.getenv("USE_EMAIL_SERVICE"),
            "MAIL_SERVER": os.getenv("MAIL_SERVER"),
            "MAIL_PORT": os.getenv("MAIL_PORT"),
            "MAIL_USE_TLS": os.getenv("MAIL_USE_TLS"),
            "MAIL_USE_SSL": os.getenv("MAIL_USE_SSL"),
            "MAIL_USERNAME": os.getenv("MAIL_USERNAME"),
            "MAIL_DEFAULT_SENDER": os.getenv("MAIL_DEFAULT_SENDER"),
            "MAIL_MAX_EMAILS": os.getenv("MAIL_MAX_EMAILS"),
            "RATELIMIT_STORAGE_URI": os.getenv("RATELIMIT_STORAGE_URI"),
            "RATELIMIT_STRATEGY": os.getenv("RATELIMIT_STRATEGY"),
            "PASSWORD_RESET_OTP_TTL_MINUTES": os.getenv(
                "PASSWORD_RESET_OTP_TTL_MINUTES"
            ),
            "PASSWORD_RESET_OTP_MAX_ATTEMPTS": os.getenv(
                "PASSWORD_RESET_OTP_MAX_ATTEMPTS"
            ),
        }
        return config, 200
