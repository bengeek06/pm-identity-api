"""
Module: customer_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating Customer model instances in the Identity Service API.

The CustomerSchema class provides field validation and metadata for the Customer
model, ensuring data integrity and proper formatting when handling API input
and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validates

from app.models.customer import Customer
from app.models.company import Company
from app.logger import logger

class CustomerSchema(SQLAlchemyAutoSchema):
    """
    Serialization and validation schema for the Customer model.

    Attributes:
        id (int): Unique identifier for the Customer entity.
        name (str): Name of the Customer entity.
        company_id (int): Foreign key to the associated Company entity.
        email (str): Email address of the Customer entity.
        contact_person (str): Optional contact person for the customer.
        phone_number (str): Optional phone number of the customer.
        address (str): Optional address of the customer.
    """
    class Meta:
        """
        Meta options for the Customer schema.
        Attributes:
            model: The SQLAlchemy model associated with this schema.
            load_instance: Whether to load model instances.
            include_fk: Whether to include foreign keys.
            dump_only: Fields that are only used for serialization.
        """
        model = Customer
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

        customer = Customer.get_by_name(value)
        if customer:
            logger.error("Validation error: Name must be unique.")
            raise ValidationError("Name must be unique.")

        return value

    @validates('company_id')
    def validate_company_id(self, value, **kwargs):
        """
        Validate that the company_id is not empty.

        Args:
            value (str): The company_id to validate.

        Raises:
            ValidationError: If the company_id is empty.

        Returns:
            str: The validated company_id.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Company ID cannot be empty.")
            raise ValidationError("Company ID cannot be empty.")
        company = Company.query.get(value)
        if not company:
            logger.error(
                f"Validation error: Company ID {value} does not exist."
            )
            raise ValidationError("Company does not exist.")

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
            raise ValidationError("Email cannot be empty.")

        customer = Customer.get_by_email(value)
        if customer:
            raise ValidationError("Email must be unique.")

        return value

    @validates('contact_person')
    def validate_contact_person(self, value, **kwargs):
        """
        Validate that the contact person does not exceed 100 characters.

        Args:
            value (str): The contact person to validate.

        Raises:
            ValidationError: If the contact person exceeds 100 characters.

        Returns:
            str: The validated contact person.
        """
        _ = kwargs

        if value and len(value) > 100:
            raise ValidationError("Contact person cannot exceed 100 characters.")

        return value

    @validates('phone_number')
    def validate_phone_number(self, value, **kwargs):
        """
        Validate that the phone number does not exceed 50 characters.

        Args:
            value (str): The phone number to validate.

        Raises:
            ValidationError: If the phone number exceeds 50 characters.

        Returns:
            str: The validated phone number.
        """
        _ = kwargs

        if value and len(value) > 50:
            raise ValidationError("Phone number cannot exceed 50 characters.")

        return value

    @validates('address')
    def validate_address(self, value, **kwargs):
        """
        Validate that the address does not exceed 255 characters.

        Args:
            value (str): The address to validate.

        Raises:
            ValidationError: If the address exceeds 255 characters.

        Returns:
            str: The validated address.
        """
        _ = kwargs

        if value and len(value) > 255:
            raise ValidationError("Address cannot exceed 255 characters.")

        return value
