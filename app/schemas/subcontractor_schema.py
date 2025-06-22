"""
Module: subcontractor_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating Subcontractor model instances in the Identity Service API.

The SubcontractorSchema class provides field validation and metadata for the
Subcontractor model, ensuring data integrity and proper formatting when
handling API input and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validates

from app.models.subcontractor import Subcontractor
from app.models.company import Company
from app.logger import logger


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

    @validates('name')
    def validate_name(self, value, **kwargs):
        """
        Validate that the name is not empty and is unique.

        Args:
            value (str): The name to validate.

        Raises:
            ValidationError: If the name is empty or already exists.

        Returns:
            str: The validated name.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Name cannot be empty.")
            raise ValidationError("Name cannot be empty.")
        subcontractor = Subcontractor.get_by_name(value)
        if subcontractor:
            logger.error(
                f"Validation error: Subcontractor with name '{value}' already exists."
            )
            raise ValidationError("Name must be unique.")
        return value

    @validates('company_id')
    def validate_company_id(self, value, **kwargs):
        """
        Validate that the company_id is not empty and exists in the Company model.

        Args:
            value (int): The company_id to validate.

        Raises:
            ValidationError: If the company_id is empty or does not exist.

        Returns:
            int: The validated company_id.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Company ID cannot be empty.")
            raise ValidationError("Company ID cannot be empty.")

        company = Company.get_by_id(value)
        if not company:
            logger.error(f"Validation error: Company with ID {value} does not exist.")
            raise ValidationError("Company ID does not exist.")

        return value

    @validates('description')
    def validate_description(self, value, **kwargs):
        """
        Validate that the description does not exceed 200 characters.

        Args:
            value (str): The description to validate.

        Raises:
            ValidationError: If the description exceeds 200 characters.

        Returns:
            str: The validated description.
        """
        _ = kwargs

        if len(value) > 200:
            logger.error("Validation error: Description cannot exceed 200 characters.")
            raise ValidationError("Description cannot exceed 200 characters.")
        return value

    @validates('email')
    def validate_email(self, value, **kwargs):
        """
        Validate that the email is not empty and is unique.

        Args:
            value (str): The email to validate.

        Raises:
            ValidationError: If the email is empty or already exists.

        Returns:
            str: The validated email.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Email cannot be empty.")
            raise ValidationError("Email cannot be empty.")

        subcontractor = Subcontractor.get_by_email(value)
        if subcontractor:
            logger.error(f"Validation error: Email '{value}' already exists.")
            raise ValidationError("Email must be unique.")

        return value

    @validates('phone_number')
    def validate_phone_number(self, value, **kwargs):
        """
        Validate that the phone number does not exceed 15 characters.

        Args:
            value (str): The phone number to validate.

        Raises:
            ValidationError: If the phone number exceeds 15 characters.

        Returns:
            str: The validated phone number.
        """
        _ = kwargs

        if value and len(value) > 15:
            logger.error("Validation error: Phone number cannot exceed 15 characters.")
            raise ValidationError("Phone number cannot exceed 15 characters.")

        return value

    @validates('address')
    def validate_address(self, value, **kwargs):
        """
        Validate that the address does not exceed 200 characters.

        Args:
            value (str): The address to validate.

        Raises:
            ValidationError: If the address exceeds 200 characters.

        Returns:
            str: The validated address.
        """
        _ = kwargs

        if value and len(value) > 200:
            logger.error("Validation error: Address cannot exceed 200 characters.")
            raise ValidationError("Address cannot exceed 200 characters.")

        return value
