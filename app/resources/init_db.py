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

from app.models import db
from app.logger import logger

from app.models.user import User
from app.models.company import Company

from app.schemas.company_schema import CompanySchema
from app.schemas.user_schema import UserSchema
from app.schemas.organization_unit_schema import OrganizationUnitSchema
from app.schemas.position_schema import PositionSchema

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
            return {"initialized": False}, 200
        else:
            return {"initialized": True}, 200

    def post(self):
        """
        Initialize the database with a company, organization unit, position,
        and admin user in a single transaction.

        This endpoint is intended to be called only once, on a fresh database.
        It expects a JSON payload containing four objects: 'company',
        'organization_unit', 'position', and 'user'. Each object must provide
        the necessary fields for its respective model. The method ensures that
        all entities are created atomically: if any step fails, the entire
        operation is rolled back.

        Request JSON structure:
            {
                "company": { ... },
                "organization_unit": { ... },
                "position": { ... },
                "user": {
                    ...,
                    "password": "plaintext_password"
                }
            }

        Behavior:
            - If the database already contains a company or user, returns 403
              and does nothing.
            - Validates and creates the company, then uses its ID to create the
              organization unit and position.
            - The user's password is hashed before storing.
            - All objects are committed in a single transaction.
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
            logger.warning("Identity database initialization attempted when already initialized.")
            return {"message": "Identity already initialized"}, 403

        json_data = request.get_json()
        company_schema = CompanySchema(session=db.session)
        org_unit_schema = OrganizationUnitSchema(session=db.session)
        position_schema = PositionSchema(session=db.session)
        user_schema = UserSchema(session=db.session)

        # Extract and validate data
        company_data = json_data.get("company")
        org_unit_data = json_data.get("organization_unit")
        position_data = json_data.get("position")
        user_data = json_data.get("user")
        if (not company_data or not org_unit_data or not position_data or
                not user_data):
            logger.error("Initialization data missing required fields.")
            return {
                "message": (
                    "'company', 'organization_unit', 'position', and 'user' "
                    "data are required."
                )
            }, 400

        try:
            with db.session.begin_nested():
                # Create company
                logger.info("Starting identity database initialization.")
                new_company = company_schema.load(company_data)
                db.session.add(new_company)
                db.session.flush()  # get new_company.id

                # Prepare and create organization unit
                logger.info("Creating organization unit.")
                json_data = request.get_json()
                json_data['organization_unit']['company_id'] = new_company.id
                new_org_unit = org_unit_schema.load(
                    json_data['organization_unit']
                )
                db.session.add(new_org_unit)
                db.session.flush()  # get new_org_unit.id

                # Prepare and create position
                logger.info("Creating position.")
                json_data['position']['company_id'] = new_company.id
                json_data['position']['organization_unit_id'] = (
                    new_org_unit.id
                )
                new_position = position_schema.load(json_data['position'])
                db.session.add(new_position)
                db.session.flush()  # get new_position.id

                # Prepare user data
                logger.info("Creating user.")
                json_data['user']['company_id'] = new_company.id
                json_data['user']['position_id'] = new_position.id
                if "password" in json_data['user']:
                    json_data['user']["hashed_password"] = (
                        generate_password_hash(json_data['user']["password"])
                    )
                    del json_data['user']["password"]
                new_user = user_schema.load(json_data['user'])
                new_user.company_id = new_company.id
                new_user.position_id = new_position.id
                db.session.add(new_user)

            db.session.commit()
            return {
                "company": company_schema.dump(new_company),
                "organization_unit": org_unit_schema.dump(new_org_unit),
                "position": position_schema.dump(new_position),
                "user": user_schema.dump(new_user)
            }, 201
        except ValidationError as err:
            db.session.rollback()
            logger.error("Validation error: %s", err.messages)
            return {
                "message": "Validation error",
                "errors": err.messages
            }, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
