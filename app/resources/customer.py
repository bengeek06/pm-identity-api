"""
Module: customer

This module defines the Flask-RESTful resources for managing Customer entities
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting customers. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.
"""

from flask import request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_restful import Resource

from app.models import db
from app.logger import logger

from app.models.customer import Customer
from app.schemas.customer_schema import CustomerSchema
from app.utils import require_jwt_auth, check_access_required


class CustomerListResource(Resource):
    """
    Resource for managing the collection of customers.

    Methods:
        get():
            Retrieve all customers from the database.

        post():
            Create a new customer with the provided data.
    """

    @require_jwt_auth(extract_company_id=False)
    @check_access_required("list")
    def get(self):
        """
        Retrieve all customers.

        Returns:
            tuple: A tuple containing a list of serialized customers and the
                   HTTP status code 200.
        """
        logger.info("Retrieving all customers")

        customers = Customer.get_all()
        customer_schema = CustomerSchema(session=db.session, many=True)
        return customer_schema.dump(customers), 200

    @require_jwt_auth(extract_company_id=True)
    @check_access_required("create")
    def post(self):
        """
        Create a new customer.

        Expects:
            JSON payload with at least the 'name' field.

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
            db.session.add(new_customer)
            db.session.commit()
            return customer_schema.dump(new_customer), 201
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"error": err.messages}, 400
        except IntegrityError as err:
            db.session.rollback()
            logger.error("Integrity error: %s", str(err))
            return {"error": "Integrity error, possibly duplicate entry."}, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error("Database error: %s", str(err))
            return {"error": "Database error occurred."}, 500


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

    @require_jwt_auth(extract_company_id=False)
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
            return {"message": "Customer not found"}, 404

        customer_schema = CustomerSchema(session=db.session)
        return customer_schema.dump(customer), 200

    @require_jwt_auth(extract_company_id=True)
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
                return {"error": "Customer not found"}, 404

            updated_customer = customer_schema.load(
                json_data, instance=customer
            )
            db.session.commit()
            return customer_schema.dump(updated_customer), 200
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"error": err.messages}, 400
        except IntegrityError as err:
            db.session.rollback()
            logger.error("Integrity error: %s", str(err))
            return {"error": "Integrity error, possibly duplicate entry."}, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error("Database error: %s", str(err))
            return {"error": "Database error occurred."}, 500

    @require_jwt_auth(extract_company_id=True)
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
                return {"error": "Customer not found"}, 404

            updated_customer = customer_schema.load(
                json_data, instance=customer, partial=True
            )
            db.session.commit()
            return customer_schema.dump(updated_customer), 200
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"error": err.messages}, 400
        except IntegrityError as err:
            db.session.rollback()
            logger.error("Integrity error: %s", str(err))
            return {"error": "Integrity error, possibly duplicate entry."}, 400
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error("Database error: %s", str(err))
            return {"error": "Database error occurred."}, 500

    @require_jwt_auth(extract_company_id=True)
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
            return {"error": "Customer not found"}, 404

        try:
            db.session.delete(customer)
            db.session.commit()
            return "", 204
        except IntegrityError as err:
            db.session.rollback()
            logger.error("Integrity error: %s", str(err))
            return (
                {"error": "Integrity error, possibly due to FK constraints."},
                400,
            )
        except SQLAlchemyError as err:
            db.session.rollback()
            logger.error("Database error: %s", str(err))
            return {"error": "Database error occurred."}, 500
