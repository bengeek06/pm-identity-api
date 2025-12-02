"""
Module: company

This module defines the Flask-RESTful resources for managing Company entities
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting companies. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.
"""

from flask import request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_restful import Resource

from app.models import db
from app.logger import logger

from app.models.company import Company
from app.schemas.company_schema import CompanySchema
from app.utils import require_jwt_auth, check_access_required


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
    @check_access_required("list")
    def get(self):
        """
        Retrieve all companies.

        Returns:
            tuple: A tuple containing a list of serialized companies and the
                   HTTP status code 200.
        """
        logger.info("Retrieving all companies")

        try:
            companies = Company.get_all()
            company_schema = CompanySchema(session=db.session, many=True)
            return company_schema.dump(companies), 200
        except SQLAlchemyError as e:
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

    @require_jwt_auth()
    @check_access_required("create")
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
    @check_access_required("read")
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
    @check_access_required("update")
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
            return {"message": "Company not found"}, 404

        company_schema = CompanySchema(context={"company": company}, session=db.session)

        try:
            company = company_schema.load(json_data, instance=company)
            db.session.commit()
            return company_schema.dump(company), 200
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

    @require_jwt_auth()
    @check_access_required("update")
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
            return {"message": "Company not found"}, 404

        company_schema = CompanySchema(
            context={"company": company}, session=db.session, partial=True
        )

        try:
            company = company_schema.load(json_data, instance=company)
            db.session.commit()
            return company_schema.dump(company), 200
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

    @require_jwt_auth()
    @check_access_required("delete")
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
            return {"message": "Company not found"}, 404

        try:
            db.session.delete(company)
            db.session.commit()
            return {}, 204
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
