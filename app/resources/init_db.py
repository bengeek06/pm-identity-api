"""
init_db.py
----------

This module defines the InitDBResource class, which exposes REST API endpoints
for initializing the identity database with a company, organization unit,
position, and admin user.

Endpoints:
    - GET /init-db: Check if the database has already been initialized
      (i.e., if at least one user exists).
    - POST /init-db: Initialize the database with the provided company,
      organization unit, position, and admin user data in a single atomic
      transaction. This endpoint is only available if the database is not
      already initialized.

The resource ensures that all entities are created atomically: if any step
fails, the entire operation is rolled back. Validation and integrity errors
are handled gracefully, and detailed error messages are returned to the client.

Typical usage:
    Register this resource with your Flask-RESTful API to allow one-time
    initialization of the identity database.
"""

from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.logger import logger
from app.models import db
from app.models.company import Company
from app.models.user import User
from app.schemas.company_schema import CompanySchema
from app.schemas.organization_unit_schema import OrganizationUnitSchema
from app.schemas.position_schema import PositionSchema
from app.schemas.user_schema import UserSchema


class InitDBResource(Resource):
    """
    Resource for initializing the database with a company, organization unit,
    position, and admin user.

    This resource exposes two endpoints:
    - GET /init-db: Check if the database has already been initialized
      (i.e., if at least one user exists).
    - POST /init-db: Initialize the database with the provided company,
      organization unit, position, and admin user data in a single transaction.
      This endpoint is only available if the database is not already
      initialized.
    """

    def get(self):
        """
        Check if the identity database has already been initialized.

        This endpoint allows clients to determine whether the initialization
        process (creation of the first company and admin user) has already
        been performed. It does so by checking if at least one user exists
        in the database.

        Returns:
            tuple: (dict, int)
                - dict: {"initialized": True} if at least one user exists,
                        {"initialized": False} otherwise.
                - int: HTTP status code 200.

        Example response:
            {"initialized": False}
        """
        user_count = User.query.count()
        if user_count == 0:
            logger.debug("Database not initialized: no users found.")
            return {"initialized": False}, 200

        logger.debug("Database initialized: users found.")
        return {"initialized": True}, 200

    @staticmethod
    def _validate_init_data(json_data):
        """
        Validate the initialization data structure.

        Args:
            json_data (dict): The JSON payload from the request.

        Returns:
            tuple: (company_data, user_data, error_response)
                - If valid: (dict, dict, None)
                - If invalid: (None, None, (dict, int))
        """
        company_data = json_data.get("company")
        user_data = json_data.get("user")
        logger.info(f"user_data content: {user_data}")

        if not company_data or not user_data:
            logger.error("Initialization data missing required fields.")
            return (
                None,
                None,
                (
                    {"message": "'company' and 'user' data are required."},
                    400,
                ),
            )
        if not isinstance(company_data, dict):
            logger.error("'company' must be a JSON object.")
            return (
                None,
                None,
                (
                    {"message": "'company' must be a JSON object."},
                    400,
                ),
            )
        if not isinstance(user_data, dict):
            logger.error("'user' must be a JSON object.")
            return (
                None,
                None,
                (
                    {"message": "'user' must be a JSON object."},
                    400,
                ),
            )

        return company_data, user_data, None

    @staticmethod
    def _create_company(company_data, company_schema):
        """
        Create and persist a new company.

        Args:
            company_data (dict): Company data to create.
            company_schema (CompanySchema): Schema for validation.

        Returns:
            Company: The created company instance.
        """
        logger.info(f"company_data type: {type(company_data)}")
        logger.info("Starting identity database initialization.")
        new_company = company_schema.load(company_data)
        db.session.add(new_company)
        db.session.flush()  # get new_company.id
        return new_company

    @staticmethod
    def _create_organization_unit(company_id, org_unit_schema):
        """
        Create a default organization unit for the company.

        Args:
            company_id (str): ID of the parent company.
            org_unit_schema (OrganizationUnitSchema): Schema for validation.

        Returns:
            OrganizationUnit: The created organization unit instance.
        """
        default_org_unit_data = {
            "name": "default organization",
        }
        logger.info(
            f"default_org_unit_data type: {type(default_org_unit_data)}"
        )
        logger.info("Creating default organization unit.")
        new_org_unit = org_unit_schema.load(default_org_unit_data)
        new_org_unit.company_id = company_id
        db.session.add(new_org_unit)
        db.session.flush()  # get new_org_unit.id
        return new_org_unit

    @staticmethod
    def _create_position(company_id, org_unit_id, position_schema):
        """
        Create a default administrator position.

        Args:
            company_id (str): ID of the parent company.
            org_unit_id (str): ID of the organization unit.
            position_schema (PositionSchema): Schema for validation.

        Returns:
            Position: The created position instance.
        """
        default_position_data = {
            "title": "Administrator",
            "organization_unit_id": org_unit_id,
        }
        logger.info(
            f"default_position_data type: {type(default_position_data)}"
        )
        logger.info("Creating default position.")
        new_position = position_schema.load(default_position_data)
        new_position.company_id = company_id
        db.session.add(new_position)
        db.session.flush()  # get new_position.id
        return new_position

    @staticmethod
    def _create_user(user_data, company_id, position_id, user_schema):
        """
        Create and persist the admin user.

        Args:
            user_data (dict): User data including password.
            company_id (str): ID of the parent company.
            position_id (str): ID of the user's position.
            user_schema (UserSchema): Schema for validation.

        Returns:
            User: The created user instance.

        Raises:
            ValidationError: If password is missing.
        """
        logger.info(f"user_data type: {type(user_data)}")
        logger.info("Creating user.")
        user_data["position_id"] = position_id

        if "password" in user_data:
            user_data["hashed_password"] = generate_password_hash(
                user_data["password"]
            )
            del user_data["password"]
        else:
            logger.error("User data missing 'password' field.")
            raise ValidationError(
                {"password": ["Missing data for required field."]}
            )

        new_user = user_schema.load(user_data)
        new_user.company_id = company_id
        new_user.position_id = position_id
        db.session.add(new_user)
        return new_user

    def post(self):
        """
        Initialize the database with a company, a default organization unit,
        a default position, and an admin user in a single transaction.

        This endpoint is intended to be called only once, on a fresh database.
        It expects a JSON payload containing two objects: 'company' and 'user'.
        The 'organization_unit' and 'position' objects are created automatically
        with the following default values:
            - organization_unit: {
                                    "name": "default organization",
                                    "company_id": <id of the created company>
                                 }
            - position: {
                            "title": "Administrator",
                            "company_id": <id of the created company>,
                            "organization_unit_id": <id of the created organization unit>
                        }

        Expected JSON structure:
            {
                "company": { ... },
                "user": {
                    ...,
                    "password": "plaintext_password"
                }
            }

        Behavior:
            - If the database already contains a company or a user, returns 403
              and does nothing.
            - Validates and creates the company, then automatically creates the
              default organization unit and position.
            - The user's password is hashed before storing.
            - All entities are created in a single atomic transaction.
            - On validation or integrity error, returns 400 with details.
            - On other database errors, returns 500.

        Returns:
            tuple: (dict, int)
                - dict: The serialized representations of the created company,
                        organization unit, position, and user.
                - int: HTTP status code (201 on success, 400/403/500 on error).

        Example success response (201):
            {
                "company": { ... },
                "organization_unit": { ... },
                "position": { ... },
                "user": { ... }
            }

        Example error response (400):
            {
                "message": "Validation error",
                "errors": { ... }
            }
        """
        if Company.query.count() != 0 or User.query.count() != 0:
            logger.warning(
                "Database initialization attempted when already initialized."
            )
            return {"message": "Identity already initialized"}, 403

        json_data = request.get_json()

        # Validate input data
        company_data, user_data, error = self._validate_init_data(json_data)
        if error:
            return error

        # Create schemas
        company_schema = CompanySchema(session=db.session)
        org_unit_schema = OrganizationUnitSchema(session=db.session)
        position_schema = PositionSchema(session=db.session)
        user_schema = UserSchema(session=db.session)

        try:
            with db.session.begin_nested():
                # Create all entities in order
                new_company = self._create_company(
                    company_data, company_schema
                )
                new_org_unit = self._create_organization_unit(
                    new_company.id, org_unit_schema
                )
                new_position = self._create_position(
                    new_company.id, new_org_unit.id, position_schema
                )
                new_user = self._create_user(
                    user_data, new_company.id, new_position.id, user_schema
                )

            db.session.commit()
            return {
                "company": company_schema.dump(new_company),
                "organization_unit": org_unit_schema.dump(new_org_unit),
                "position": position_schema.dump(new_position),
                "user": user_schema.dump(new_user),
            }, 201
        except ValidationError as err:
            db.session.rollback()
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
