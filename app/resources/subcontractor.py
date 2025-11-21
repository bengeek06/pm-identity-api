# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
module: subcontractor

This module defines the Flask-RESTful resources for managing Subcontractor
entities in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting subcontractors. The resources use Marshmallow schemas
for validation and serialization, and handle database errors gracefully.
"""

from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.constants import (LOG_DATABASE_ERROR, LOG_INTEGRITY_ERROR,
                           LOG_VALIDATION_ERROR, MSG_DATABASE_ERROR,
                           MSG_INTEGRITY_ERROR, MSG_SUBCONTRACTOR_DELETED,
                           MSG_SUBCONTRACTOR_NOT_FOUND, MSG_VALIDATION_ERROR)
from app.logger import logger
from app.models import db
from app.models.subcontractor import Subcontractor
from app.schemas.subcontractor_schema import SubcontractorSchema
from app.utils import check_access_required, require_jwt_auth

# Error message constants
ERROR_SUBCONTRACTOR_NOT_FOUND = "Subcontractor with ID %s not found"


class SubcontractorListResource(Resource):
    """
    Resource for managing the collection of subcontractors.

    Methods:
        get():
            Retrieve all subcontractors from the database.

        post():
            Create a new subcontractor with the provided data.
    """

    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """
        Retrieve all subcontractors with optional filtering, pagination, and sorting.

        Query Parameters:
            name (str, optional): Filter by exact subcontractor name match
            page (int, optional): Page number (default: 1, min: 1)
            limit (int, optional): Items per page (default: 50, max: 1000)
            sort (str, optional): Field to sort by (created_at, updated_at, name)
            order (str, optional): Sort order (asc, desc, default: asc)

        Returns:
            tuple: Paginated response with data and metadata, HTTP 200
        """
        try:
            query = Subcontractor.query

            # Apply name filter if provided
            name = request.args.get("name")
            if name:
                query = query.filter_by(name=name)

            # Pagination parameters
            page = request.args.get("page", 1, type=int)
            limit = request.args.get("limit", 50, type=int)

            # Validate and constrain pagination params
            page = max(1, page)
            limit = min(max(1, limit), 1000)

            # Sorting parameters
            sort_field = request.args.get("sort", "created_at")
            sort_order = request.args.get("order", "asc")

            # Validate sort field
            allowed_sorts = ["created_at", "updated_at", "name"]
            if sort_field not in allowed_sorts:
                sort_field = "created_at"

            # Apply sorting
            if sort_order == "desc":
                query = query.order_by(
                    getattr(Subcontractor, sort_field).desc()
                )
            else:
                query = query.order_by(
                    getattr(Subcontractor, sort_field).asc()
                )

            # Execute pagination
            paginated = query.paginate(
                page=page, per_page=limit, error_out=False
            )

            schema = SubcontractorSchema(many=True)
            return {
                "data": schema.dump(paginated.items),
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": paginated.total,
                    "pages": paginated.pages,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }, 200
        except SQLAlchemyError as e:
            logger.error("Error fetching subcontractors: %s", str(e))
            return {"message": "Error fetching subcontractors"}, 500

    @require_jwt_auth()
    @check_access_required("create")
    def post(self):
        """
        Create a new subcontractor.

        Expects:
            JSON payload with at least the 'name' field.
            company_id is automatically extracted from JWT token.

        Returns:
            tuple: The serialized created subcontractor and HTTP status code
                   201 on success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new subcontractor")

        json_data = request.get_json()
        subcontractor_schema = SubcontractorSchema(session=db.session)

        try:
            new_subcontractor = subcontractor_schema.load(json_data)
            # Assign company_id from JWT after load
            new_subcontractor.company_id = g.company_id
            db.session.add(new_subcontractor)
            db.session.commit()
            return subcontractor_schema.dump(new_subcontractor), 201
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


class SubcontractorResource(Resource):
    """
    Resource for managing a single subcontractor.

    Methods:
        get(subcontractor_id):
            Retrieve a subcontractor by ID.

        put(subcontractor_id):
            Update an existing subcontractor by ID.

        patch(subcontractor_id):
            Partially update an existing subcontractor by ID.

        delete(subcontractor_id):
            Delete a subcontractor by ID.
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, subcontractor_id):
        """
        Retrieve a subcontractor by ID.

        Args:
            subcontractor_id (str): The ID of the subcontractor to retrieve.

        Returns:
            tuple: The serialized subcontractor and HTTP status code 200 on
                   success. HTTP status code 404 if the subcontractor is not
                   found.
        """
        logger.info("Fetching subcontractor with ID: %s", subcontractor_id)

        subcontractor = Subcontractor.get_by_id(subcontractor_id)
        if not subcontractor:
            logger.warning(ERROR_SUBCONTRACTOR_NOT_FOUND, subcontractor_id)
            return {"error": MSG_SUBCONTRACTOR_NOT_FOUND}, 404

        schema = SubcontractorSchema(session=db.session)
        return schema.dump(subcontractor), 200

    @require_jwt_auth()
    @check_access_required("update")
    def put(self, subcontractor_id):
        """
        Update a subcontractor by ID.

        Expects:
            JSON payload with fields to update.

        Args:
            subcontractor_id (str): The ID of the subcontractor to update.

        Returns:
            tuple: The serialized updated subcontractor and HTTP status code
                   200 on success.
                   HTTP status code 404 if the subcontractor is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info("Updating subcontractor with ID: %s", subcontractor_id)

        json_data = request.get_json()
        subcontractor_schema = SubcontractorSchema(session=db.session)

        try:
            subcontractor = Subcontractor.get_by_id(subcontractor_id)
            if not subcontractor:
                logger.warning(ERROR_SUBCONTRACTOR_NOT_FOUND, subcontractor_id)
                return {"error": MSG_SUBCONTRACTOR_NOT_FOUND}, 404

            updated_subcontractor = subcontractor_schema.load(
                json_data, instance=subcontractor
            )
            db.session.commit()
            return subcontractor_schema.dump(updated_subcontractor), 200
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

    @require_jwt_auth()
    @check_access_required("update")
    def patch(self, subcontractor_id):
        """
        Partially update a subcontractor by ID.

        Expects:
            JSON payload with fields to update.

        Args:
            subcontractor_id (str): The ID of the subcontractor to update.

        Returns:
            tuple: The serialized updated subcontractor and HTTP status code
                   200 on success.
                   HTTP status code 404 if the subcontractor is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info(
            "Partially updating subcontractor with ID: %s", subcontractor_id
        )

        json_data = request.get_json()
        subcontractor_schema = SubcontractorSchema(
            session=db.session, partial=True
        )

        try:
            subcontractor = Subcontractor.get_by_id(subcontractor_id)
            if not subcontractor:
                logger.warning(ERROR_SUBCONTRACTOR_NOT_FOUND, subcontractor_id)
                return {"message": MSG_SUBCONTRACTOR_NOT_FOUND}, 404

            updated_subcontractor = subcontractor_schema.load(
                json_data, instance=subcontractor, partial=True
            )
            db.session.commit()
            return subcontractor_schema.dump(updated_subcontractor), 200
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

    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, subcontractor_id):
        """
        Delete a subcontractor by ID.

        Args:
            subcontractor_id (str): The ID of the subcontractor to delete.

        Returns:
            tuple: Message and HTTP status code 204 on success,
                   or error message and code on failure.
        """
        subcontractor = Subcontractor.get_by_id(subcontractor_id)
        if not subcontractor:
            logger.warning(ERROR_SUBCONTRACTOR_NOT_FOUND, subcontractor_id)
            return {"message": MSG_SUBCONTRACTOR_NOT_FOUND}, 404

        try:
            db.session.delete(subcontractor)
            db.session.commit()
            return {"message": MSG_SUBCONTRACTOR_DELETED}, 204
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500
