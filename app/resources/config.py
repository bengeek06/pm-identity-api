"""
config.py
---------

This module defines the ConfigResource for exposing the current application
configuration through a REST endpoint.
"""

import os
from flask_restful import Resource
from app.utils import require_jwt_auth, check_access_required


class ConfigResource(Resource):
    """
    Resource for providing the application configuration.

    Methods:
        get():
            Retrieve the current application configuration.
    """

    @require_jwt_auth(extract_company_id=False)
    @check_access_required("read")
    def get(self):
        """
        Retrieve the current application configuration.

        Returns:
            dict: A dictionary containing the application configuration and
            HTTP status code 200.
        """
        config = {
            "FLASK_ENV": os.getenv("FLASK_ENV"),
            "DEBUG": os.getenv("DEBUG"),
            "DATABASE_URI": os.getenv("DATABASE_URI"),
        }
        return config, 200
