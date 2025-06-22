"""
Module: user_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating User model instances in the Identity Service API.

The UserSchema class provides field validation and metadata for the User
model, ensuring data integrity and proper formatting when handling API input
and output.
"""

from datetime import datetime
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validates

from app.models.user import User
from app.models.company import Company
from app.models.position import Position
from app.logger import logger


class UserSchema(SQLAlchemyAutoSchema):
    """
    Serialization and validation schema for the User model.

    Attributes:
        id (int): Unique identifier for the User entity.
        email (str): Email address of the user (required, unique).
        hashed_password (str): Hashed password for authentication.
        first_name (str): Optional first name of the user.
        last_name (str): Optional last name of the user.
        phone_number (str): Optional phone number of the user.
        avatar_url (str): Optional URL to the user's avatar.
        is_active (bool): Whether the user account is active.
        is_verifed (bool): Whether the user's email is verified.
        last_login_at (datetime): Timestamp of the user's last login.
        company_id (str): Foreign key referencing the associated company.
        position_id (str): Foreign key referencing the user's position.
    """
    class Meta:
        """
        Meta options for the User schema.

        Attributes:
            model: The SQLAlchemy model associated with this schema.
            load_instance: Whether to load model instances.
            include_fk: Whether to include foreign keys.
            dump_only: Fields that are only used for serialization.
        """
        model = User
        load_instance = True
        include_fk = True
        dump_only = ('id', 'created_at', 'updated_at')

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
        user = User.get_by_email(value)
        if user:
            logger.error(
                f"Validation error: User with email '{value}' already exists."
            )
            raise ValidationError("Email already exists.")
        return value

    @validates('company_id')
    def validate_company_id(self, value, **kwargs):
        """
        Validate that the company_id is not empty and exists in the Company
        model.

        Args:
            value (str): The company_id to validate.

        Raises:
            ValidationError: If the company_id is empty or does not exist.

        Returns:
            str: The validated company_id.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Company ID cannot be empty.")
            raise ValidationError("Company ID cannot be empty.")
        company = Company.get_by_id(value)
        if not company:
            logger.error(
                f"Validation error: Company with ID '{value}' does not exist."
            )
            raise ValidationError("Company does not exist.")
        return value

    @validates('position_id')
    def validate_position_id(self, value, **kwargs):
        """
        Validate that the position_id is not empty and exists in the Position
        model.

        Args:
            value (str): The position_id to validate.

        Raises:
            ValidationError: If the position_id is empty or does not exist.

        Returns:
            str: The validated position_id.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Position ID cannot be empty.")
            raise ValidationError("Position ID cannot be empty.")
        position = Position.get_by_id(value)
        if not position:
            logger.error(
               f"Validation error: Position with ID '{value}' does not exist."
            )
            raise ValidationError("Position does not exist.")
        return value

    @validates('first_name')
    def validate_first_name(self, value, **kwargs):
        """
        Validate that the first_name is not empty.

        Args:
            value (str): The first name to validate.

        Raises:
            ValidationError: If the first name is empty.

        Returns:
            str: The validated first name.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: First name cannot be empty.")
            raise ValidationError("First name cannot be empty.")
        if len(value) > 50:
            logger.error(
                "Validation error: First name cannot exceed 50 characters."
            )
            raise ValidationError("First name cannot exceed 50 characters.")
        return value

    @validates('last_name')
    def validate_last_name(self, value, **kwargs):
        """
        Validate that the last_name is not empty.

        Args:
            value (str): The last name to validate.

        Raises:
            ValidationError: If the last name is empty.

        Returns:
            str: The validated last name.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Last name cannot be empty.")
            raise ValidationError("Last name cannot be empty.")
        if len(value) > 50:
            logger.error(
                "Validation error: Last name cannot exceed 50 characters."
            )
            raise ValidationError("Last name cannot exceed 50 characters.")
        return value

    @validates('phone_number')
    def validate_phone_number(self, value, **kwargs):
        """
        Validate that the phone_number does not exceed 50 characters.

        Args:
            value (str): The phone number to validate.

        Raises:
            ValidationError: If the phone number exceeds 50 characters.

        Returns:
            str: The validated phone number.
        """
        _ = kwargs

        if value and len(value) > 50:
            logger.error(
                "Validation error: Phone number cannot exceed 50 characters."
            )
            raise ValidationError("Phone number cannot exceed 50 characters.")
        return value

    @validates('avatar_url')
    def validate_avatar_url(self, value, **kwargs):
        """
        Validate that the avatar_url does not exceed 255 characters.

        Args:
            value (str): The avatar URL to validate.

        Raises:
            ValidationError: If the avatar URL exceeds 255 characters.

        Returns:
            str: The validated avatar URL.
        """
        _ = kwargs

        if value and len(value) > 255:
            logger.error(
                "Validation error: Avatar URL cannot exceed 255 characters."
            )
            raise ValidationError("Avatar URL cannot exceed 255 characters.")
        if value and not value.startswith(('http://', 'https://')):
            logger.error("Validation error: Avatar URL must be a valid URL.")
            raise ValidationError("Avatar URL must be a valid URL.")
        return value

    @validates('hashed_password')
    def validate_hashed_password(self, value, **kwargs):
        """
        Validate that the hashed_password is not empty.

        Args:
            value (str): The hashed password to validate.

        Raises:
            ValidationError: If the hashed password is empty.

        Returns:
            str: The validated hashed password.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Hashed password cannot be empty.")
            raise ValidationError("Hashed password cannot be empty.")
        return value

    @validates('is_active')
    def validate_is_active(self, value, **kwargs):
        """
        Validate that the is_active field is a boolean.

        Args:
            value (bool): The is_active value to validate.

        Raises:
            ValidationError: If the value is not a boolean.

        Returns:
            bool: The validated is_active value.
        """
        _ = kwargs

        if not isinstance(value, bool):
            logger.error("Validation error: is_active must be a boolean.")
            raise ValidationError("is_active must be a boolean.")
        return value

    @validates('is_verified')
    def validate_is_verified(self, value, **kwargs):
        """
        Validate that the is_verified field is a boolean.

        Args:
            value (bool): The is_verified value to validate.

        Raises:
            ValidationError: If the value is not a boolean.

        Returns:
            bool: The validated is_verified value.
        """
        _ = kwargs

        if not isinstance(value, bool):
            logger.error("Validation error: is_verified must be a boolean.")
            raise ValidationError("is_verified must be a boolean.")
        return value

    @validates('last_login_at')
    def validate_last_login_at(self, value, **kwargs):
        """
        Validate that the last_login_at field is a datetime.

        Args:
            value (datetime): The last_login_at value to validate.

        Raises:
            ValidationError: If the value is not a datetime.

        Returns:
            datetime: The validated last_login_at value.
        """
        _ = kwargs

        if value and not isinstance(value, datetime):
            logger.error("Validation error: last_login_at must be a datetime.")
            raise ValidationError("last_login_at must be a datetime.")
        return value
