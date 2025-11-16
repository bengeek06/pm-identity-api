"""
module: app.resources.user_position

This module defines Flask-RESTful resources for managing users by position
in the Identity Service API.

It provides endpoints for retrieving users associated with specific positions.
"""

from flask_restful import Resource
from sqlalchemy.exc import SQLAlchemyError

from app.logger import logger
from app.models.user import User
from app.schemas.user_schema import UserSchema
from app.utils import check_access_required, require_jwt_auth


class UserPositionResource(Resource):
    """
    Resource for handling users by position.

    Methods:
        get(position_id):
            Retrieve all users for a specific position.
    """

    @require_jwt_auth()
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
