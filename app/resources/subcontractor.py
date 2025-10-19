"""
module: subcontractor

This module defines the Flask-RESTful resources for managing Subcontractor
entities in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting subcontractors. The resources use Marshmallow schemas
for validation and serialization, and handle database errors gracefully.
"""

from flask import request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_restful import Resource

from app.models import db
from app.logger import logger
from app.models.subcontractor import Subcontractor
from app.schemas.subcontractor_schema import SubcontractorSchema


class SubcontractorListResource(Resource):
    """
    Resource for managing the collection of subcontractors.

    Methods:
        get():
            Retrieve all subcontractors from the database.

        post():
            Create a new subcontractor with the provided data.
    """

    def get(self):
        """
        Retrieve all subcontractors.

        Returns:
            tuple: A tuple containing a list of serialized subcontractors and
                   the HTTP status code 200.
        """
        try:
            subcontractors = Subcontractor.query.all()
            schema = SubcontractorSchema(many=True)
            return schema.dump(subcontractors), 200
        except SQLAlchemyError as e:
            logger.error("Error fetching subcontractors: %s", str(e))
            return {"message": "Error fetching subcontractors"}, 500

    def post(self):
        """
        Create a new subcontractor.

        Expects:
            JSON payload with at least the 'name' and 'company_id' fields.

        Returns:
            tuple: The serialized created subcontractor and HTTP status code
                   201 on success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new subcontractor")

        json_data = request.get_json()
        subcontractor_schema = SubcontractorSchema(session=db.session)

        try:
            subcontractor = subcontractor_schema.load(json_data)
            db.session.add(subcontractor)
            db.session.commit()
            return subcontractor_schema.dump(subcontractor), 201
        except ValidationError as e:
            logger.error("Validation error: %s", e.messages)
            return {"message": "Validation error", "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e.orig))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500


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
            logger.warning(
                "Subcontractor with ID %s not found", subcontractor_id
            )
            return {"message": "Subcontractor not found"}, 404

        schema = SubcontractorSchema(session=db.session)
        return schema.dump(subcontractor), 200

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
                logger.warning(
                    "Subcontractor with ID %s not found", subcontractor_id
                )
                return {"message": "Subcontractor not found"}, 404

            updated_subcontractor = subcontractor_schema.load(
                json_data, instance=subcontractor
            )
            db.session.commit()
            return subcontractor_schema.dump(updated_subcontractor), 200
        except ValidationError as e:
            logger.error("Validation error: %s", e.messages)
            return {"message": "Validation error", "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e.orig))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

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
                logger.warning(
                    "Subcontractor with ID %s not found", subcontractor_id
                )
                return {"message": "Subcontractor not found"}, 404

            updated_subcontractor = subcontractor_schema.load(
                json_data, instance=subcontractor, partial=True
            )
            db.session.commit()
            return subcontractor_schema.dump(updated_subcontractor), 200
        except ValidationError as e:
            logger.error("Validation error: %s", e.messages)
            return {"message": "Validation error", "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e.orig))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

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
            logger.warning(
                "Subcontractor with ID %s not found", subcontractor_id
            )
            return {"message": "Subcontractor not found"}, 404

        try:
            db.session.delete(subcontractor)
            db.session.commit()
            return {"message": "Subcontractor deleted successfully"}, 204
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
