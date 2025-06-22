"""
Module: company_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating Company model instances in the Identity Service API.

The CompanySchema class provides field validation and metadata for the Company
model, ensuring data integrity and proper formatting when handling API input
and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validates

from app.models.company import Company
from app.logger import logger


class CompanySchema(SQLAlchemyAutoSchema):
    """
    Serialization and validation schema for the Company model.

    Attributes:
        id (int): Unique identifier for the Company entity.
        name (str): Name of the Company entity.
        description (str): Description of the Company entity.
        logo_url (str): Optional URL to the company's logo.
        website (str): Optional website URL of the company.
        phone_number (str): Optional phone number of the company.
        email (str): Optional email address of the company.
        address (str): Optional address of the company.
        postal_code (str): Optional postal code of the company.
        city (str): Optional city where the company is located.
        country (str): Optional country where the company is located.
        users (list): Relationship to User objects belonging to the company.
        organizations_units (list): Relationship to OrganizationUnit objects
                belonging to the company.
    """
    class Meta:
        """
        Meta options for the Company schema.

        Attributes:
            model: The SQLAlchemy model associated with this schema.
            load_instance: Whether to load model instances.
            include_fk: Whether to include foreign keys.
            dump_only: Fields that are only used for serialization.
        """
        model = Company
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
        company = Company.get_by_name(value)
        if company:
            logger.error(f"Validation error: Name '{value}' must be unique.")
            raise ValidationError("Name must be unique.")
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
            logger.error(
                "Validation error: Description cannot exceed 200 characters."
            )
            raise ValidationError("Description cannot exceed 200 characters.")
        return value

    @validates('logo_url')
    def validate_logo_url(self, value, **kwargs):
        """
        Validate that the logo URL is a valid URL format.

        Args:
            value (str): The logo URL to validate.

        Raises:
            ValidationError: If the logo URL is not a valid URL.

        Returns:
            str: The validated logo URL.
        """
        _ = kwargs

        if value and not value.startswith(('http://', 'https://')):
            logger.error("Validation error: Logo URL must be a valid URL.")
            raise ValidationError("Logo URL must be a valid URL.")
        if value and len(value) > 255:
            logger.error(
                "Validation error: Logo URL cannot exceed 255 characters."
            )
            raise ValidationError("Logo URL cannot exceed 255 characters.")
        return value

    @validates('website')
    def validate_website(self, value, **kwargs):
        """
        Validate that the website URL is a valid URL format.

        Args:
            value (str): The website URL to validate.

        Raises:
            ValidationError: If the website URL is not a valid URL.

        Returns:
            str: The validated website URL.
        """
        _ = kwargs

        if value and not value.startswith(('http://', 'https://')):
            logger.error("Validation error: Website must be a valid URL.")
            raise ValidationError("Website must be a valid URL.")
        if value and len(value) > 255:
            logger.error(
                "Validation error: Website cannot exceed 255 characters."
            )
            raise ValidationError("Website cannot exceed 255 characters.")
        return value

    @validates('phone_number')
    def validate_phone_number(self, value, **kwargs):
        """
        Validate that the phone number is in a valid format.

        Args:
            value (str): The phone number to validate.

        Raises:
            ValidationError: If the phone number is not valid.

        Returns:
            str: The validated phone number.
        """
        _ = kwargs

        if value and not value.isdigit():
            logger.error(
                "Validation error: Phone number must contain only digits."
            )
            raise ValidationError("Phone number must contain only digits.")
        if value and len(value) > 20:
            logger.error(
                "Validation error: Phone number cannot exceed 20 characters."
            )
            raise ValidationError("Phone number cannot exceed 20 characters.")
        return value

    @validates('email')
    def validate_email(self, value, **kwargs):
        """
        Validate that the email is in a valid format.

        Args:
            value (str): The email to validate.

        Raises:
            ValidationError: If the email is not valid.

        Returns:
            str: The validated email.
        """
        _ = kwargs

        if value and '@' not in value:
            logger.error(
                "Validation error: Email must be a valid email address."
                )
            raise ValidationError("Email must be a valid email address.")
        if value and len(value) > 255:
            logger.error(
                "Validation error: Email cannot exceed 255 characters."
                )
            raise ValidationError("Email cannot exceed 255 characters.")
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
            logger.error(
                "Validation error: Address cannot exceed 255 characters."
            )
            raise ValidationError("Address cannot exceed 255 characters.")
        return value

    @validates('postal_code')
    def validate_postal_code(self, value, **kwargs):
        """
        Validate that the postal code does not exceed 20 characters.

        Args:
            value (str): The postal code to validate.

        Raises:
            ValidationError: If the postal code exceeds 20 characters.

        Returns:
            str: The validated postal code.
        """
        _ = kwargs

        if value and len(value) > 20:
            logger.error(
                "Validation error: Postal code cannot exceed 20 characters."
            )
            raise ValidationError("Postal code cannot exceed 20 characters.")
        return value

    @validates('city')
    def validate_city(self, value, **kwargs):
        """
        Validate that the city does not exceed 100 characters.

        Args:
            value (str): The city to validate.

        Raises:
            ValidationError: If the city exceeds 100 characters.

        Returns:
            str: The validated city.
        """
        _ = kwargs

        if value and len(value) > 100:
            logger.error(
                "Validation error: City cannot exceed 100 characters."
            )
            raise ValidationError("City cannot exceed 100 characters.")
        return value

    @validates('country')
    def validate_country(self, value, **kwargs):
        """
        Validate that the country does not exceed 100 characters.

        Args:
            value (str): The country to validate.

        Raises:
            ValidationError: If the country exceeds 100 characters.

        Returns:
            str: The validated country.
        """
        _ = kwargs

        if value and len(value) > 100:
            logger.error(
                "Validation error: Country cannot exceed 100 characters."
            )
            raise ValidationError("Country cannot exceed 100 characters.")
        return value
