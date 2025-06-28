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
from marshmallow import ValidationError, validates, fields, validate

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

    id = fields.UUID(dump_only=True)
    email = fields.Email(required=True, validate=validate.Length(max=100))
    hashed_password = fields.String(required=True, validate=validate.Length(max=255))
    first_name = fields.String(required=True, validate=validate.Length(max=50))
    last_name = fields.String(required=True, validate=validate.Length(max=50))
    phone_number = fields.String(validate=validate.Length(max=50), allow_none=True)
    avatar_url = fields.String(validate=validate.Length(max=255), allow_none=True)
    is_active = fields.Boolean(load_default=True, dump_default=True)
    is_verified = fields.Boolean(load_default=False, dump_default=False)
    last_login_at = fields.DateTime(allow_none=True)
    company_id = fields.String(
        required=True,
        validate=validate.Regexp(
            r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
            error="Organization Unit ID must be a valid UUID."
        )
    )
    position_id = fields.String(
        required=False,
        validate=validate.Regexp(
            r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
            error="Organization Unit ID must be a valid UUID."
        )
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates('email')
    def validate_email(self, value, **kwargs):
        """
        Validate that the email is unique.

        Args:
            value (str): The email to validate.

        Raises:
            ValidationError: If the email already exists.

        Returns:
            str: The validated email.
        """
        _ = kwargs

        user = User.get_by_email(value)
        if user:
            logger.error(
                f"Validation error: User with email '{value}' already exists."
            )
            raise ValidationError("Email already exists.")
        return value

    