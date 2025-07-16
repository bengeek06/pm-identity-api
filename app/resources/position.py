"""
module: position

This module defines the Flask-RESTful resources for managing Position entities
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting positions, as well as listing and creating positions
within a specific organization unit. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.
"""

from flask import request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_restful import Resource

from app.models import db
from app.logger import logger
from app.models.position import Position
from app.schemas.position_schema import PositionSchema
from app.models.organization_unit import OrganizationUnit


class PositionListResource(Resource):
    """
    Resource for managing the collection of positions.

    Methods:
        get():
            Retrieve all positions from the database.

        post():
            Create a new position with the provided data.
    """
    def get(self):
        """
        Retrieve all positions.

        Returns:
            tuple: A tuple containing a list of serialized positions and the
                   HTTP status code 200.
        """
        try:
            positions = Position.query.all()
            schema = PositionSchema(many=True)
            return schema.dump(positions), 200
        except SQLAlchemyError as e:
            logger.error("Error fetching positions: %s", str(e))
            return {"message": "Error fetching positions"}, 500

    def post(self):
        """
        Create a new position.

        Expects:
            JSON payload with au moins 'title' et 'organization_unit_id'.
            Le champ company_id est automatiquement renseigné.

        Returns:
            tuple: The serialized created position and HTTP status code 201
                   on success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new position")

        json_data = request.get_json()
        org_unit_id = json_data.get('organization_unit_id')
        if not org_unit_id:
            logger.warning("organization_unit_id is required")
            return {"message": "organization_unit_id is required"}, 400

        org_unit = OrganizationUnit.get_by_id(org_unit_id)
        if not org_unit:
            logger.warning("Organization unit with ID %s not found", org_unit_id)
            return {"message": "Organization unit not found"}, 404

        position_schema = PositionSchema(session=db.session)

        try:
            position = position_schema.load(json_data)
            # Renseigne company_id sur l'instance après le load
            position.company_id = org_unit.company_id
            db.session.add(position)
            db.session.commit()
            return position_schema.dump(position), 201
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


class PositionResource(Resource):
    """
    Resource for managing a single position.

    Methods:
        get(position_id):
            Retrieve a position by ID.

        put(position_id):
            Update an existing position by ID.

        patch(position_id):
            Partially update an existing position by ID.

        delete(position_id):
            Delete a position by ID.
    """
    def get(self, position_id):
        """
        Retrieve a position by ID.

        Args:
            position_id (str): The ID of the position to retrieve.

        Returns:
            tuple: The serialized position and HTTP status code 200 on success.
                   HTTP status code 404 if the position is not found.
        """
        logger.info("Retrieving position with ID: %s", position_id)

        position = Position.get_by_id(position_id)
        if not position:
            logger.warning("Position with ID %s not found", position_id)
            return {"message": "Position not found"}, 404

        schema = PositionSchema(session=db.session)
        return schema.dump(position), 200

    def put(self, position_id):
        """
        Update an existing position with the provided data.

        Expects:
            JSON payload with at least the 'title' and 'company_id' fields.

        Args:
            position_id (str): The ID of the position to update.

        Returns:
            tuple: The serialized updated position and HTTP status code 200
                   on success.
            tuple: Error message and HTTP status code 400 or 404 on failure.
        """
        logger.info("Updating position with ID: %s", position_id)

        json_data = request.get_json()
        position_schema = PositionSchema(session=db.session)

        try:
            position = Position.get_by_id(position_id)
            if not position:
                logger.warning("Position with ID %s not found", position_id)
                return {"message": "Position not found"}, 404

            position = position_schema.load(json_data, instance=position)
            db.session.commit()
            return position_schema.dump(position), 200
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"message": "Validation error", "errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

    def patch(self, position_id):
        """
        Partially update an existing position with the provided data.

        Expects:
            JSON payload with fields to update.

        Args:
            position_id (str): The ID of the position to update.

        Returns:
            tuple: The serialized updated position and HTTP status code 200
                   on success.
            tuple: Error message and HTTP status code 400 or 404 on failure.
        """
        logger.info("Partially updating position with ID: %s", position_id)

        json_data = request.get_json()
        position_schema = PositionSchema(session=db.session, partial=True)

        try:
            position = Position.get_by_id(position_id)
            if not position:
                logger.warning("Position with ID %s not found", position_id)
                return {"message": "Position not found"}, 404

            position = position_schema.load(json_data, instance=position)
            db.session.commit()
            return position_schema.dump(position), 200
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"message": "Validation error", "errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

    def delete(self, position_id):
        """
        Delete a position by ID.

        Args:
            position_id (str): The ID of the position to delete.

        Returns:
            tuple: Message and HTTP status code 204 on success,
                   or error message and code on failure.
        """
        position = Position.get_by_id(position_id)
        if not position:
            logger.warning("Position with ID %s not found", position_id)
            return {"message": "Position not found"}, 404

        try:
            db.session.delete(position)
            db.session.commit()
            return {"message": "Position deleted"}, 204
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500


class OrganizationUnitPositionsResource(Resource):
    """
    Resource for managing positions within a specific organization unit.

    Methods:
        get(unit_id):
            List all positions for a given organization unit.

        post(unit_id):
            Create a new position for a given organization unit.
    """
    def get(self, unit_id):
        """
        List all positions for a given organization unit.

        Args:
            unit_id (str): The ID of the organization unit.

        Returns:
            tuple: List of serialized positions and HTTP status code 200.
        """
        positions = Position.get_by_organization_unit_id(
            organization_unit_id=unit_id
        )
        schema = PositionSchema(many=True)
        return schema.dump(positions), 200

    def post(self, unit_id):
        """
        Create a new position for a given organization unit.

        Args:
            unit_id (str): The ID of the organization unit.

        Returns:
            tuple: The serialized created position and HTTP status code 201
                   on success.
            tuple: Error message and HTTP status code 400 or 404 on failure.
        """
        # Vérifie que l'unité existe et récupère-la
        org_unit = OrganizationUnit.get_by_id(unit_id)
        if not org_unit:
            logger.warning("Organization unit with ID %s not found", unit_id)
            return {"error": "Organization unit not found"}, 404

        json_data = request.get_json()
        # Renseigne automatiquement organization_unit_id
        json_data['organization_unit_id'] = unit_id
        position_schema = PositionSchema(session=db.session)
        try:
            position = position_schema.load(json_data)
            # Renseigne company_id sur l'instance après le load
            position.company_id = org_unit.company_id
            db.session.add(position)
            db.session.commit()
            return position_schema.dump(position), 201
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
