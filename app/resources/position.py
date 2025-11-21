# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
module: position

This module defines the Flask-RESTful resources for managing Position entities
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting positions, as well as listing and creating positions
within a specific organization unit. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.
"""

from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.constants import (LOG_DATABASE_ERROR, LOG_INTEGRITY_ERROR,
                           LOG_VALIDATION_ERROR, MSG_DATABASE_ERROR,
                           MSG_INTEGRITY_ERROR, MSG_POSITION_NOT_FOUND,
                           MSG_VALIDATION_ERROR)
from app.logger import logger
from app.models import db
from app.models.organization_unit import OrganizationUnit
from app.models.position import Position
from app.schemas.position_schema import PositionSchema
from app.utils import check_access_required, require_jwt_auth


def validate_organization_unit_ownership(org_unit, org_unit_id):
    """
    Validate that an organization unit belongs to the authenticated company.

    Args:
        org_unit: The OrganizationUnit instance to validate
        org_unit_id (str): The organization unit ID for logging

    Returns:
        tuple: (error_dict, status_code) if validation fails, None otherwise
    """
    if org_unit.company_id != g.company_id:
        logger.warning(
            "Organization unit %s does not belong to company %s",
            org_unit_id,
            g.company_id,
        )
        return {
            "message": "Organization unit does not belong to your company"
        }, 403
    return None


class PositionListResource(Resource):
    """
    Resource for managing the collection of positions.

    Methods:
        get():
            Retrieve all positions from the database.

        post():
            Create a new position with the provided data.
    """

    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """
        Retrieve all positions with optional filtering.

        Query Parameters:
            title (str, optional): Filter by exact position title match

        Returns:
            tuple: A tuple containing a list of serialized positions and the
                   HTTP status code 200.
        """
        try:
            query = Position.query

            # Apply title filter if provided
            title = request.args.get("title")
            if title:
                query = query.filter_by(title=title)

            positions = query.all()
            schema = PositionSchema(many=True)
            return schema.dump(positions), 200
        except SQLAlchemyError as e:
            logger.error("Error fetching positions: %s", str(e))
            return {"message": "Error fetching positions"}, 500

    @require_jwt_auth()
    @check_access_required("create")
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
        org_unit_id = json_data.get("organization_unit_id")
        if not org_unit_id:
            logger.warning("organization_unit_id is required")
            return {"message": "organization_unit_id is required"}, 400

        org_unit = OrganizationUnit.get_by_id(org_unit_id)
        if not org_unit:
            logger.warning(
                "Organization unit with ID %s not found", org_unit_id
            )
            return {"message": "Organization unit not found"}, 404

        # Valider que l'organization_unit appartient à la company du JWT
        validation_error = validate_organization_unit_ownership(
            org_unit, org_unit_id
        )
        if validation_error:
            return validation_error

        position_schema = PositionSchema(session=db.session)

        try:
            position = position_schema.load(json_data)
            # Assigner company_id depuis JWT (pattern standard)
            position.company_id = g.company_id
            db.session.add(position)
            db.session.commit()
            return position_schema.dump(position), 201
        except ValidationError as e:
            logger.error(LOG_VALIDATION_ERROR, e.messages)
            return {"message": MSG_VALIDATION_ERROR, "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(e.orig))
            return {"message": MSG_INTEGRITY_ERROR}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500


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

    @require_jwt_auth()
    @check_access_required("read")
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
            return {"message": MSG_POSITION_NOT_FOUND}, 404

        schema = PositionSchema(session=db.session)
        return schema.dump(position), 200

    @require_jwt_auth()
    @check_access_required("update")
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
                return {"message": MSG_POSITION_NOT_FOUND}, 404

            position = position_schema.load(json_data, instance=position)
            db.session.commit()
            return position_schema.dump(position), 200
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, err.messages)
            return {
                "message": MSG_VALIDATION_ERROR,
                "errors": err.messages,
            }, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(e))
            return {"message": MSG_INTEGRITY_ERROR}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500

    @require_jwt_auth()
    @check_access_required("update")
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
                return {"message": MSG_POSITION_NOT_FOUND}, 404

            position = position_schema.load(json_data, instance=position)
            db.session.commit()
            return position_schema.dump(position), 200
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, err.messages)
            return {
                "message": MSG_VALIDATION_ERROR,
                "errors": err.messages,
            }, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(e))
            return {"message": MSG_INTEGRITY_ERROR}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500

    @require_jwt_auth()
    @check_access_required("delete")
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
            return {"message": MSG_POSITION_NOT_FOUND}, 404

        try:
            db.session.delete(position)
            db.session.commit()
            return {"message": "Position deleted"}, 204
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500


class OrganizationUnitPositionsResource(Resource):
    """
    Resource for managing positions within a specific organization unit.

    Methods:
        get(unit_id):
            List all positions for a given organization unit.

        post(unit_id):
            Create a new position for a given organization unit.
    """

    @require_jwt_auth()
    @check_access_required("list")
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

    @require_jwt_auth()
    @check_access_required("create")
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
            return {"message": "Organization unit not found"}, 404

        # Valider que l'organization_unit appartient à la company du JWT
        validation_error = validate_organization_unit_ownership(
            org_unit, unit_id
        )
        if validation_error:
            return validation_error

        json_data = request.get_json()
        # Renseigne automatiquement organization_unit_id
        json_data["organization_unit_id"] = unit_id
        position_schema = PositionSchema(session=db.session)
        try:
            position = position_schema.load(json_data)
            # Assigner company_id depuis JWT (pattern standard)
            position.company_id = g.company_id
            db.session.add(position)
            db.session.commit()
            return position_schema.dump(position), 201
        except ValidationError as e:
            logger.error(LOG_VALIDATION_ERROR, e.messages)
            return {"message": MSG_VALIDATION_ERROR, "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(e.orig))
            return {"message": MSG_INTEGRITY_ERROR}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500
