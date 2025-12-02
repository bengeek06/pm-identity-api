# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
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
from sqlalchemy.orm import joinedload

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
from app.schemas.organization_unit_schema import (
    OrganizationUnitNestedSchema,
    OrganizationUnitSchema,
)
from app.schemas.position_schema import PositionNestedSchema
from app.utils import check_access_required, parse_expand, require_jwt_auth


# Allowed expansions for organization unit endpoints
ORG_UNIT_ALLOWED_EXPANSIONS = {"positions", "parent", "children"}


def _empty_paginated_response():
    """Return an empty paginated response."""
    return {
        "data": [],
        "pagination": {
            "page": 1,
            "limit": 50,
            "total": 0,
            "pages": 0,
            "has_next": False,
            "has_prev": False,
        },
    }


def _get_pagination_params():
    """Extract and validate pagination parameters from request."""
    page = max(1, request.args.get("page", 1, type=int))
    limit = min(max(1, request.args.get("limit", 50, type=int)), 1000)
    return page, limit


def _apply_sorting(query, model, extra_fields=None):
    """Apply sorting to query based on request parameters."""
    allowed_sorts = ["created_at", "updated_at"] + (extra_fields or [])
    sort_field = request.args.get("sort", "created_at")
    if sort_field not in allowed_sorts:
        sort_field = "created_at"
    sort_order = request.args.get("order", "asc")
    column = getattr(model, sort_field)
    return query.order_by(column.desc() if sort_order == "desc" else column.asc())


def _build_pagination_meta(paginated, page, limit):
    """Build pagination metadata dictionary."""
    return {
        "page": page,
        "limit": limit,
        "total": paginated.total,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
        "has_prev": paginated.has_prev,
    }


def _build_org_unit_query_with_expansions(query, expansions):
    """Apply eager loading options to query based on requested expansions."""
    if "positions" in expansions:
        query = query.options(joinedload(OrganizationUnit.positions))
    if "parent" in expansions:
        query = query.options(joinedload(OrganizationUnit.parent))
    if "children" in expansions:
        query = query.options(joinedload(OrganizationUnit.children))
    return query


def _apply_org_unit_filters(query, id__in, name, search):
    """Apply filters to organization unit query."""
    if id__in is not None:
        ids = [uuid.strip() for uuid in id__in.split(",") if uuid.strip()]
        if ids:
            query = query.filter(OrganizationUnit.id.in_(ids))
    if name:
        query = query.filter_by(name=name)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                OrganizationUnit.name.ilike(search_pattern),
                OrganizationUnit.description.ilike(search_pattern),
            )
        )
    return query


def _apply_org_unit_expansions(data, items, expansions):
    """Apply expansion data to serialized organization units."""
    if not expansions:
        return
    position_schema = PositionNestedSchema(many=True)
    nested_schema = OrganizationUnitNestedSchema()
    nested_schema_many = OrganizationUnitNestedSchema(many=True)

    for i, org_unit in enumerate(items):
        if "positions" in expansions:
            data[i]["positions"] = position_schema.dump(org_unit.positions)
        if "parent" in expansions:
            data[i]["parent"] = (
                nested_schema.dump(org_unit.parent) if org_unit.parent else None
            )
        if "children" in expansions:
            data[i]["children"] = nested_schema_many.dump(org_unit.children)


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
    @check_access_required("LIST")
    def get(self):
        """
        Retrieve all organization units with optional filtering, pagination, and sorting.

        Query Parameters:
            id__in (str, optional): Comma-separated list of UUIDs to filter by
            name (str, optional): Filter by exact organization unit name match
            search (str, optional): Search in name and description
            page (int, optional): Page number (default: 1, min: 1)
            limit (int, optional): Items per page (default: 50, max: 1000)
            sort (str, optional): Field to sort by (created_at, updated_at, name, level)
            order (str, optional): Sort order (asc, desc, default: asc)
            expand (str, optional): Comma-separated list of relations to expand
                                    (e.g., positions,parent,children)

        Returns:
            tuple: Paginated response with data and metadata, HTTP 200
        """
        logger.info("Retrieving all organization units")

        try:
            # Parse expand parameter and get filters
            expansions = parse_expand(
                request.args.get("expand"), ORG_UNIT_ALLOWED_EXPANSIONS
            )
            id__in = request.args.get("id__in")

            # Handle empty id__in filter
            if id__in is not None and id__in.strip() == "":
                return _empty_paginated_response(), 200

            # Build query with expansions and filters
            query = _build_org_unit_query_with_expansions(
                OrganizationUnit.query, expansions
            )
            query = _apply_org_unit_filters(
                query,
                id__in,
                request.args.get("name"),
                request.args.get("search"),
            )

            # Get pagination and sorting params
            page, limit = _get_pagination_params()
            query = _apply_sorting(query, OrganizationUnit, ["name", "level"])

            # Execute pagination
            paginated = query.paginate(page=page, per_page=limit, error_out=False)

            # Serialize and apply expansions
            schema = OrganizationUnitSchema(session=db.session, many=True)
            data = schema.dump(paginated.items)
            _apply_org_unit_expansions(data, paginated.items, expansions)

            return {
                "data": data,
                "pagination": _build_pagination_meta(paginated, page, limit),
            }, 200
        except SQLAlchemyError as e:
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR_OCCURRED}, 500

    @require_jwt_auth()
    @check_access_required("CREATE")
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
    @check_access_required("READ")
    def get(self, unit_id):
        """
        Retrieve an organization unit by its ID.

        Args:
            unit_id (str): The ID of the organization unit.

        Query Parameters:
            expand (str, optional): Comma-separated list of relations to expand
                                    (e.g., positions,parent,children)

        Returns:
            tuple: The serialized organization unit and HTTP status code 200
                   on success.
                   HTTP status code 404 if the organization unit is not found.
        """
        logger.info("Retrieving organization unit with ID %s", unit_id)

        # Parse expand parameter
        expand_param = request.args.get("expand")
        expansions = parse_expand(expand_param, ORG_UNIT_ALLOWED_EXPANSIONS)

        # Build query with optional eager loading
        query = OrganizationUnit.query.filter_by(id=unit_id)
        if "positions" in expansions:
            query = query.options(joinedload(OrganizationUnit.positions))
        if "parent" in expansions:
            query = query.options(joinedload(OrganizationUnit.parent))
        if "children" in expansions:
            query = query.options(joinedload(OrganizationUnit.children))

        org_unit = query.first()
        if not org_unit:
            logger.warning("Organization unit with ID %s not found", unit_id)
            return {"error": MSG_ORG_UNIT_NOT_FOUND}, 404

        org_unit_schema = OrganizationUnitSchema(session=db.session)
        data = org_unit_schema.dump(org_unit)

        # Apply expansions
        if "positions" in expansions:
            position_schema = PositionNestedSchema(many=True)
            data["positions"] = position_schema.dump(org_unit.positions)
        if "parent" in expansions:
            nested_schema = OrganizationUnitNestedSchema()
            if org_unit.parent:
                data["parent"] = nested_schema.dump(org_unit.parent)
            else:
                data["parent"] = None
        if "children" in expansions:
            nested_schema_many = OrganizationUnitNestedSchema(many=True)
            data["children"] = nested_schema_many.dump(org_unit.children)

        return data, 200

    @require_jwt_auth()
    @check_access_required("UPDATE")
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
    @check_access_required("UPDATE")
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
    @check_access_required("DELETE")
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
    @check_access_required("LIST")
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
