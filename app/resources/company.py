# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Module: company

This module defines the Flask-RESTful resources for managing Company entities
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting companies. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.
"""

from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.constants import (LOG_DATABASE_ERROR, LOG_INTEGRITY_ERROR,
                           LOG_VALIDATION_ERROR, MSG_COMPANY_NOT_FOUND,
                           MSG_DATABASE_ERROR, MSG_INTEGRITY_ERROR,
                           MSG_VALIDATION_ERROR)
from app.logger import logger
from app.models import db
from app.models.company import Company
from app.schemas.company_schema import CompanySchema
from app.utils import check_access_required, require_jwt_auth


class CompanyListResource(Resource):
    """
    Resource for managing the collection of companies.

    Methods:
        get():
            Retrieve all companies from the database.

        post():
            Create a new company with the provided data.
    """

    @require_jwt_auth()
    @check_access_required("LIST")
    def get(self):
        """
        Retrieve all companies with optional filtering, pagination, and sorting.

        Query Parameters:
            name (str, optional): Filter by exact company name match
            search (str, optional): Search in name and description
            page (int, optional): Page number (default: 1, min: 1)
            limit (int, optional): Items per page (default: 50, max: 1000)
            sort (str, optional): Field to sort by (created_at, updated_at, name)
            order (str, optional): Sort order (asc, desc, default: asc)

        Returns:
            tuple: Paginated response with data and metadata, HTTP 200
        """
        logger.info("Retrieving all companies")

        try:
            query = Company.query

            # Apply name filter if provided
            name = request.args.get("name")
            if name:
                query = query.filter_by(name=name)

            # Apply search filter if provided (searches in name and description)
            search = request.args.get("search")
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    db.or_(
                        Company.name.ilike(search_pattern),
                        Company.description.ilike(search_pattern),
                    )
                )

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
                query = query.order_by(getattr(Company, sort_field).desc())
            else:
                query = query.order_by(getattr(Company, sort_field).asc())

            # Execute pagination
            paginated = query.paginate(
                page=page, per_page=limit, error_out=False
            )

            company_schema = CompanySchema(session=db.session, many=True)
            return {
                "data": company_schema.dump(paginated.items),
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
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500

    @require_jwt_auth()
    @check_access_required("CREATE")
    def post(self):
        """
        Create a new company.

        Expects:
            JSON payload with at least the 'name' field.

        Returns:
            tuple: The serialized created company and HTTP status code 201
                   on success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new company")

        json_data = request.get_json()
        company_schema = CompanySchema(session=db.session)

        try:
            new_company = company_schema.load(json_data)
            db.session.add(new_company)
            db.session.commit()
            return company_schema.dump(new_company), 201
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


class CompanyResource(Resource):
    """
    Resource for managing a single company.

    Methods:
        get(company_id):
            Retrieve a specific company by its ID.

        put(company_id):
            Update an existing company with the provided data.

        patch(company_id):
            Partially update an existing company with the provided data.

        delete(company_id):
            Delete a specific company by its ID.
    """

    @require_jwt_auth()
    @check_access_required("READ")
    def get(self, company_id):
        """
        Retrieve a specific company by its ID.

        Args:
            company_id (str): The ID of the company to retrieve.

        Returns:
            tuple: The serialized company and HTTP status code 200 on success.
            tuple: Error message and HTTP status code 404 if not found.
        """
        logger.info("Retrieving company with ID: %s", company_id)

        company = Company.get_by_id(company_id)
        if not company:
            logger.warning("Company with ID %s not found", company_id)
            return {"message": "Company not found"}, 404

        company_schema = CompanySchema(session=db.session)
        return company_schema.dump(company), 200

    @require_jwt_auth()
    @check_access_required("UPDATE")
    def put(self, company_id):
        """
        Update an existing company with the provided data.

        Expects:
            JSON payload with at least the 'name' field.

        Args:
            company_id (str): The ID of the company to update.

        Returns:
            tuple: The serialized updated company and HTTP status code 200 on
                   success.
            tuple: Error message and HTTP status code 400 or 404 on failure.
        """
        logger.info("Updating company with ID: %s", company_id)

        json_data = request.get_json()
        company = Company.get_by_id(company_id)
        if not company:
            logger.warning("Company with ID %s not found", company_id)
            return {"message": MSG_COMPANY_NOT_FOUND}, 404

        company_schema = CompanySchema(
            context={"company": company}, session=db.session
        )

        try:
            company = company_schema.load(json_data, instance=company)
            db.session.commit()
            return company_schema.dump(company), 200
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
    @check_access_required("UPDATE")
    def patch(self, company_id):
        """
        Partially update an existing company with the provided data.

        Expects:
            JSON payload with fields to update.

        Args:
            company_id (str): The ID of the company to update.

        Returns:
            tuple: The serialized updated company and HTTP status code 200 on
                   success.
            tuple: Error message and HTTP status code 400 or 404 on failure.
        """
        logger.info("Partially updating company with ID: %s", company_id)

        json_data = request.get_json()
        company = Company.get_by_id(company_id)
        if not company:
            logger.warning("Company with ID %s not found", company_id)
            return {"message": MSG_COMPANY_NOT_FOUND}, 404

        company_schema = CompanySchema(
            context={"company": company}, session=db.session, partial=True
        )

        try:
            company = company_schema.load(json_data, instance=company)
            db.session.commit()
            return company_schema.dump(company), 200
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
    @check_access_required("DELETE")
    def delete(self, company_id):
        """
        Delete a specific company by its ID.

        Args:
            company_id (str): The ID of the company to delete.

        Returns:
            tuple: Empty dict and HTTP status code 204 on success.
            tuple: Error message and HTTP status code 404 if not found.
        """
        logger.info("Deleting company with ID: %s", company_id)

        company = Company.get_by_id(company_id)
        if not company:
            logger.warning("Company with ID %s not found", company_id)
            return {"message": MSG_COMPANY_NOT_FOUND}, 404

        try:
            db.session.delete(company)
            db.session.commit()
            return {}, 204
        except IntegrityError as e:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(e))
            return {"message": MSG_INTEGRITY_ERROR}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500
