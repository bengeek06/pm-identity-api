"""
Module: subcontractor_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating Subcontractor model instances in the Identity Service API.

The SubcontractorSchema class provides field validation and metadata for the
Subcontractor model, ensuring data integrity and proper formatting when
handling API input and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validate, fields, validates

from app.logger import logger
from app.models.subcontractor import Subcontractor


class SubcontractorSchema(SQLAlchemyAutoSchema):
    """
    Serialization and validation schema for the Subcontractor model.

    Attributes:
        id (int): Unique identifier for the Subcontractor entity.
        name (str): Name of the subcontractor.
        description (str): Description of the subcontractor.
        company_id (int): Foreign key to the associated company.
        contact_person (str): Optional contact person for the subcontractor.
        phone_number (str): Optional phone number of the subcontractor.
        email (str): Optional email address of the subcontractor.
        address (str): Optional address of the subcontractor.
    """
    class Meta:
        """
        Meta options for the Subcontractor schema.

        Attributes:
            model: The SQLAlchemy model associated with this schema.
            load_instance: Whether to load model instances.
            include_fk: Whether to include foreign keys.
            dump_only: Fields that are only used for serialization.
        """
        model = Subcontractor
        load_instance = True
        include_fk = True
        dump_only = ('id', 'created_at', 'updated_at')

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100, error="Name must be between 1 and 100 characters."),
    )

    description = fields.String(
        required=False,
        validate=validate.Length(max=200, error="Description cannot exceed 200 characters."),
    )

    company_id = fields.String(
        required=True,
        validate=validate.Regexp(
            r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
            error="Organization Unit ID must be a valid UUID."
        )
    )

    contact_person = fields.String(
        required=False,
        validate=validate.Length(max=100, error="Contact person cannot exceed 100 characters."),
    )

    phone_number = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=50),
            validate.Regexp(
                r"^\d*$", error="Phone number must contain only digits.")
        ]
    )

    email = fields.Email(
        required=False,
        validate=validate.Length(max=100, error="Email cannot exceed 100 characters."),
    )

    address = fields.String(
        required=False,
        validate=validate.Length(max=200, error="Address cannot exceed 200 characters."),
    )

    @validates('name')
    def validate_name(self, value, **kwargs):
        """
        Validate that the name is not empty and is unique.

        Args:
            value (str): The name to validate.

        Raises:
            ValidationError: If the name already exists.

        Returns:
            str: The validated name.
        """
        _ = kwargs

        subcontractor = Subcontractor.get_by_name(value)
        if subcontractor:
            logger.error(
                f"Validation error: Subcontractor with name '{value}' already exists."
            )
            raise ValidationError("Name must be unique.")
        return value
