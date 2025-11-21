"""
module: organization_unit

This module defines the Flask-RESTful resources for managing OrganizationUnit
entities in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting organization units, as well as listing their children.
The resources use Marshmallow schemas for validation and serialization, and
handle database errors gracefully.
"""

from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.constants import (
    LOG_DATABASE_ERROR,
    LOG_INTEGRITY_ERROR,
    LOG_VALIDATION_ERROR,
    MSG_DATABASE_ERROR_OCCURRED,
    MSG_INTEGRITY_ERROR_DUPLICATE,
    MSG_ORG_UNIT_NOT_FOUND,
)
from app.logger import logger
from app.models import db
from app.models.organization_unit import OrganizationUnit
from app.schemas.organization_unit_schema import OrganizationUnitSchema
from app.utils import check_access_required, require_jwt_auth


class OrganizationUnitListResource(Resource):
    """
    Resource for managing the collection of organization units.

    Methods:
        get():
            Retrieve all organization units from the database.

        post():
            Create a new organization unit with the provided data.
    """

    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """
        Retrieve all organization units.

        Returns:
            tuple: A tuple containing a list of serialized organization units
            and the HTTP status code 200.
        """
        logger.info("Retrieving all organization units")

        org_units = OrganizationUnit.get_all()
        org_unit_schema = OrganizationUnitSchema(session=db.session, many=True)
        return org_unit_schema.dump(org_units), 200

    @require_jwt_auth()
    @check_access_required("create")
    def post(self):
        """
        Create a new organization unit.

        Expects:
            JSON payload with at least the 'name' field.
            company_id is automatically extracted from JWT token.

        Returns:
            tuple: The serialized created organization unit and HTTP status
                   code 201 on success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new organization unit")
        json_data = request.get_json()
        org_unit_schema = OrganizationUnitSchema(session=db.session)
        org_unit_schema.context = {}

        try:
            new_org_unit = org_unit_schema.load(json_data)
            # Assign company_id from JWT after load
            new_org_unit.company_id = g.company_id
            db.session.add(new_org_unit)
            db.session.flush()
            new_org_unit.update_path_and_level()
            db.session.commit()
            return org_unit_schema.dump(new_org_unit), 201
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, str(err))
            return {"error": str(err)}, 400
        except IntegrityError as err:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(err))
            return {"error": MSG_INTEGRITY_ERROR_DUPLICATE}, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(err))
            return {"error": MSG_DATABASE_ERROR_OCCURRED}, 500


class OrganizationUnitResource(Resource):
    """
    Resource for managing a single organization unit.

    Methods:
        get(unit_id):
            Retrieve an organization unit by its ID.

        put(unit_id):
            Update an existing organization unit by its ID.

        patch(unit_id):
            Partially update an existing organization unit by its ID.

        delete(unit_id):
            Delete an organization unit by its ID, including all its
            descendants.
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, unit_id):
        """
        Retrieve an organization unit by its ID.

        Args:
            unit_id (str): The ID of the organization unit.

        Returns:
            tuple: The serialized organization unit and HTTP status code 200
                   on success.
                   HTTP status code 404 if the organization unit is not found.
        """
        logger.info("Retrieving organization unit with ID %s", unit_id)

        org_unit = OrganizationUnit.get_by_id(unit_id)
        if not org_unit:
            logger.warning("Organization unit with ID %s not found", unit_id)
            return {"error": MSG_ORG_UNIT_NOT_FOUND}, 404

        org_unit_schema = OrganizationUnitSchema(session=db.session)
        return org_unit_schema.dump(org_unit), 200

    @require_jwt_auth()
    @check_access_required("update")
    def put(self, unit_id):
        """
        Update an existing organization unit by its ID.

        Args:
            unit_id (str): The ID of the organization unit to update.

        Expects:
            JSON payload with fields to update.

        Returns:
            tuple: The serialized updated organization unit and HTTP status
                   code 200 on success.
                   HTTP status code 404 if the organization unit is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info("Updating organization unit with ID %s", unit_id)
        json_data = request.get_json()
        org_unit_schema = OrganizationUnitSchema(session=db.session)
        org_unit_schema.context = {"current_id": unit_id}

        try:
            org_unit = OrganizationUnit.get_by_id(unit_id)
            if not org_unit:
                logger.warning(
                    "Organization unit with ID %s not found", unit_id
                )
                return {"error": MSG_ORG_UNIT_NOT_FOUND}, 404

            updated_org_unit = org_unit_schema.load(
                json_data, instance=org_unit
            )
            updated_org_unit.context = {"current_id": unit_id}
            updated_org_unit.update_path_and_level()
            db.session.commit()
            return org_unit_schema.dump(updated_org_unit), 200
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, str(err))
            return {"error": str(err)}, 400
        except IntegrityError as err:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(err))
            return {"error": MSG_INTEGRITY_ERROR_DUPLICATE}, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(err))
            return {"error": MSG_DATABASE_ERROR_OCCURRED}, 500

    @require_jwt_auth()
    @check_access_required("update")
    def patch(self, unit_id):
        """
        Partially update an existing organization unit by its ID.

        Args:
            unit_id (str): The ID of the organization unit to update.

        Expects:
            JSON payload with fields to update.

        Returns:
            tuple: The serialized updated organization unit and HTTP status
                   code 200 on success.
                   HTTP status code 404 if the organization unit is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info("Partially updating organization unit with ID %s", unit_id)
        json_data = request.get_json()
        org_unit_schema = OrganizationUnitSchema(
            session=db.session, partial=True
        )
        org_unit_schema.context = {"current_id": unit_id}
        try:
            org_unit = OrganizationUnit.get_by_id(unit_id)
            if not org_unit:
                logger.warning(
                    "Organization unit with ID %s not found", unit_id
                )
                return {"error": MSG_ORG_UNIT_NOT_FOUND}, 404

            # Passe le contexte pour la validation de parent_id
            updated_org_unit = org_unit_schema.load(
                json_data, instance=org_unit
            )
            updated_org_unit.update_path_and_level()
            db.session.commit()
            return org_unit_schema.dump(updated_org_unit), 200
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, str(err))
            return {"error": str(err)}, 400
        except IntegrityError as err:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(err))
            return {"error": MSG_INTEGRITY_ERROR_DUPLICATE}, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(err))
            return {"error": MSG_DATABASE_ERROR_OCCURRED}, 500

    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, unit_id):
        """
        Delete an organization unit by its ID, including all its descendants.

        Args:
            unit_id (str): The ID of the organization unit to delete.

        Returns:
            tuple: HTTP status code 204 on success.
                   HTTP status code 404 if the organization unit is not found.
        """
        logger.info(
            "Deleting organization unit with ID %s and all its descendants",
            unit_id,
        )

        org_unit = OrganizationUnit.get_by_id(unit_id)
        if not org_unit:
            logger.warning("Organization unit with ID %s not found", unit_id)
            return {"error": MSG_ORG_UNIT_NOT_FOUND}, 404

        try:
            # Suppression récursive des enfants
            def delete_descendants(unit):
                """
                Recursively delete all descendants of the given organization
                unit.

                Args:
                    unit (OrganizationUnit): The parent organization unit.
                """
                children = OrganizationUnit.get_children(unit.id)
                for child in children:
                    delete_descendants(child)
                    db.session.delete(child)

            delete_descendants(org_unit)
            db.session.delete(org_unit)
            db.session.commit()
            return "", 204
        except IntegrityError as err:
            db.session.rollback()
            logger.error(
                "Integrity error while deleting organization unit: %s",
                str(err),
            )
            return {
                "error": "Integrity error, possibly due to FK constraints."
            }, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error(
                "Database error while deleting organization unit: %s", str(err)
            )
            return {"error": MSG_DATABASE_ERROR_OCCURRED}, 500


class OrganizationUnitChildrenResource(Resource):
    """
    Resource for managing the children of an organization unit.

    Methods:
        get(unit_id):
            Retrieve all children of a specific organization unit.
    """

    @require_jwt_auth()
    @check_access_required("list")
    def get(self, unit_id):
        """
        Retrieve all children of a specific organization unit.

        Args:
            unit_id (str): The ID of the parent organization unit.

        Returns:
            tuple: A list of serialized child organization units and HTTP
                   status code 200.
        """
        logger.info(
            "Retrieving children of organization unit with ID %s", unit_id
        )

        children = OrganizationUnit.get_children(unit_id)
        org_unit_schema = OrganizationUnitSchema(session=db.session, many=True)
        return org_unit_schema.dump(children), 200
