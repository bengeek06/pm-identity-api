"""
user_schema.py
--------------

This module defines the Marshmallow schema for serializing, deserializing,
and validating User model instances in the Identity Service API.

The UserSchema class provides field validation and metadata for the User
model, ensuring data integrity and proper formatting when handling API input
and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validates, fields, validate

from app.models.user import User
from app.logger import logger


class UserSchema(SQLAlchemyAutoSchema):
    """
    Marshmallow schema for the User model.

    This schema serializes and validates User objects, enforces field types,
    length constraints, and format (email, UUID, etc.), and ensures proper
    deserialization/serialization for API input/output.

    Attributes:
        id (UUID): Unique identifier for the User entity.
        email (str): Email address of the user (required, unique).
        hashed_password (str): Hashed password for authentication (load only).
        first_name (str, optional): First name of the user.
        last_name (str, optional): Last name of the user.
        phone_number (str, optional): Phone number of the user.
        avatar_url (str, optional): URL to the user's avatar.
        is_active (bool): Whether the user account is active.
        is_verified (bool): Whether the user's email is verified.
        last_login_at (datetime, optional): Timestamp of the user's last login.
        company_id (str): Foreign key referencing the associated company (UUID).
        position_id (str, optional): Foreign key referencing the user's position (UUID).
        created_at (datetime): Timestamp when the user was created.
        updated_at (datetime): Timestamp when the user was last updated.
    """
    # Permet le passage explicite du contexte lors de l'instanciation
    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context', {})
        super().__init__(*args, **kwargs)

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
    hashed_password = fields.String(
        required=True,
        validate=validate.Length(max=255),
        load_only=True
    )
    first_name = fields.String(validate=validate.Length(max=50))
    last_name = fields.String(validate=validate.Length(max=50))
    phone_number = fields.String(
        validate=validate.Length(max=50),
        allow_none=True
    )
    avatar_url = fields.String(
        validate=validate.Length(max=255),
        allow_none=True
    )
    is_active = fields.Boolean(load_default=True, dump_default=True)
    is_verified = fields.Boolean(load_default=False, dump_default=False)
    last_login_at = fields.DateTime(allow_none=True)
    company_id = fields.String(
        required=True,
        validate=validate.Regexp(
            r'^[a-fA-F0-9]{8}-'
            r'[a-fA-F0-9]{4}-'
            r'[a-fA-F0-9]{4}-'
            r'[a-fA-F0-9]{4}-'
            r'[a-fA-F0-9]{12}$',
            error="Company ID must be a valid UUID."
        )
    )
    position_id = fields.String(
        required=False,
        validate=validate.Regexp(
            r'^[a-fA-F0-9]{8}-'
            r'[a-fA-F0-9]{4}-'
            r'[a-fA-F0-9]{4}-'
            r'[a-fA-F0-9]{4}-'
            r'[a-fA-F0-9]{12}$',
            error="Position ID must be a valid UUID."
        )
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates('email')
    def validate_email(self, value, **kwargs):
        """
        Validate that the email is unique, except for the current user (on update).

        Args:
            value (str): The email to validate.

        Raises:
            ValidationError: If the email already exists for another user.

        Returns:
            str: The validated email.
        """
        _ = kwargs

        user = User.get_by_email(value)
        current_user = self.context.get('user') if hasattr(self, 'context') else None
        if user and (not current_user or user.id != getattr(current_user, 'id', None)):
            logger.error(
                "Validation error: User with email '%s' already exists.",
                value
            )
            raise ValidationError("Email already exists.")
        return value
