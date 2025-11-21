# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Module: customer

This module defines the Flask-RESTful resources for managing Customer entities
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting customers. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.
"""

from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.constants import (LOG_DATABASE_ERROR, LOG_INTEGRITY_ERROR,
                           LOG_VALIDATION_ERROR, MSG_CUSTOMER_NOT_FOUND,
                           MSG_DATABASE_ERROR_OCCURRED,
                           MSG_INTEGRITY_ERROR_DUPLICATE)
from app.logger import logger
from app.models import db
from app.models.customer import Customer
from app.schemas.customer_schema import CustomerSchema
from app.utils import check_access_required, require_jwt_auth


class CustomerListResource(Resource):
    """
    Resource for managing the collection of customers.

    Methods:
        get():
            Retrieve all customers from the database.

        post():
            Create a new customer with the provided data.
    """

    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """
        Retrieve all customers with optional filtering, pagination, and sorting.

        Query Parameters:
            name (str, optional): Filter by exact customer name match
            page (int, optional): Page number (default: 1, min: 1)
            limit (int, optional): Items per page (default: 50, max: 1000)
            sort (str, optional): Field to sort by (created_at, updated_at, name)
            order (str, optional): Sort order (asc, desc, default: asc)

        Returns:
            tuple: Paginated response with data and metadata, HTTP 200
        """
        logger.info("Retrieving all customers")

        try:
            query = Customer.query

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
                query = query.order_by(getattr(Customer, sort_field).desc())
            else:
                query = query.order_by(getattr(Customer, sort_field).asc())

            # Execute pagination
            paginated = query.paginate(
                page=page, per_page=limit, error_out=False
            )

            customer_schema = CustomerSchema(session=db.session, many=True)
            return {
                "data": customer_schema.dump(paginated.items),
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
            return {"message": MSG_DATABASE_ERROR_OCCURRED}, 500

    @require_jwt_auth()
    @check_access_required("create")
    def post(self):
        """
        Create a new customer.

        Expects:
            JSON payload with at least the 'name' field.
            company_id is automatically extracted from JWT token.

        Returns:
            tuple: The serialized created customer and HTTP status code 201
                   on success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new customer")

        json_data = request.get_json()
        customer_schema = CustomerSchema(session=db.session)

        try:
            new_customer = customer_schema.load(json_data)
            # Assign company_id from JWT after load
            new_customer.company_id = g.company_id
            db.session.add(new_customer)
            db.session.commit()
            return customer_schema.dump(new_customer), 201
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, err.messages)
            return {"error": err.messages}, 400
        except IntegrityError as err:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(err))
            return {"error": MSG_INTEGRITY_ERROR_DUPLICATE}, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(err))
            return {"error": MSG_DATABASE_ERROR_OCCURRED}, 500


class CustomerResource(Resource):
    """
    Resource for managing a single customer.

    Methods:
        get(customer_id):
            Retrieve a customer by ID.

        put(customer_id):
            Update an existing customer by ID.

        patch(customer_id):
            Partially update an existing customer by ID.

        delete(customer_id):
            Delete a customer by ID.
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, customer_id):
        """
        Retrieve a customer by ID.

        Args:
            customer_id (int): The ID of the customer to retrieve.

        Returns:
            tuple: The serialized customer and HTTP status code 200 on success.
                   HTTP status code 404 if the customer is not found.
        """
        logger.info("Retrieving customer with ID %s", customer_id)

        customer = Customer.get_by_id(customer_id)
        if not customer:
            logger.warning("Customer with ID %s not found", customer_id)
            return {"message": MSG_CUSTOMER_NOT_FOUND}, 404

        customer_schema = CustomerSchema(session=db.session)
        return customer_schema.dump(customer), 200

    @require_jwt_auth()
    @check_access_required("update")
    def put(self, customer_id):
        """
        Update an existing customer by ID.

        Args:
            customer_id (int): The ID of the customer to update.

        Returns:
            tuple: The serialized updated customer and HTTP status code 200 on
                   success.
            tuple: Error message and HTTP status code 404 if not found or 400
                   for validation errors.
        """
        logger.info("Updating customer with ID %s", customer_id)

        json_data = request.get_json()
        customer_schema = CustomerSchema(session=db.session)

        try:
            customer = Customer.get_by_id(customer_id)
            if not customer:
                logger.warning("Customer with ID %s not found", customer_id)
                return {"error": MSG_CUSTOMER_NOT_FOUND}, 404

            updated_customer = customer_schema.load(
                json_data, instance=customer
            )
            db.session.commit()
            return customer_schema.dump(updated_customer), 200
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, err.messages)
            return {"error": err.messages}, 400
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
    def patch(self, customer_id):
        """
        Partially update an existing customer by ID.

        Args:
            customer_id (int): The ID of the customer to update.

        Returns:
            tuple: The serialized updated customer and HTTP status code 200 on
                   success.
            tuple: Error message and HTTP status code 404 if not found or 400
                   for validation errors.
        """
        logger.info("Partially updating customer with ID %s", customer_id)

        json_data = request.get_json()
        customer_schema = CustomerSchema(session=db.session, partial=True)

        try:
            customer = Customer.get_by_id(customer_id)
            if not customer:
                logger.warning("Customer with ID %s not found", customer_id)
                return {"error": MSG_CUSTOMER_NOT_FOUND}, 404

            updated_customer = customer_schema.load(
                json_data, instance=customer, partial=True
            )
            db.session.commit()
            return customer_schema.dump(updated_customer), 200
        except ValidationError as err:
            logger.error(LOG_VALIDATION_ERROR, err.messages)
            return {"error": err.messages}, 400
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
    def delete(self, customer_id):
        """
        Delete a customer by ID.

        Args:
            customer_id (int): The ID of the customer to delete.

        Returns:
            tuple: HTTP status code 204 on success.
                   HTTP status code 404 if the customer is not found.
        """
        logger.info("Deleting customer with ID %s", customer_id)

        customer = Customer.get_by_id(customer_id)
        if not customer:
            logger.warning("Customer with ID %s not found", customer_id)
            return {"error": MSG_CUSTOMER_NOT_FOUND}, 404

        try:
            db.session.delete(customer)
            db.session.commit()
            return "", 204
        except IntegrityError as err:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(err))
            return (
                {"error": "Integrity error, possibly due to FK constraints."},
                400,
            )
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(err))
            return {"error": MSG_DATABASE_ERROR_OCCURRED}, 500
