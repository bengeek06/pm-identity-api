"""
Schema definition for the Company model using Marshmallow.

This module provides the CompanySchema class, which serializes and validates
Company objects for API input/output. It enforces field types, length constraints,
formats (email, URL, digits), and ensures the uniqueness of the company name.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, validate, RAISE, validates, ValidationError
from app.models.company import Company

class CompanySchema(SQLAlchemyAutoSchema):
    """
    Marshmallow schema for the Company model.

    This schema serializes and validates Company objects, enforcing field types,
    length constraints, and format (email, URL, digits). It also ensures the
    uniqueness of the company name via a custom validator.

    Fields:
        name (str): Required. 1-100 characters.
        description (str): Optional. Max 200 characters.
        logo_url (str): Optional. Must be a valid URL, max 255 characters.
        website (str): Optional. Must be a valid URL, max 255 characters.
        phone_number (str): Optional. Digits only, max 20 characters.
        email (str): Optional. Must be a valid email, max 255 characters.
        address (str): Optional. Max 255 characters.
        postal_code (str): Optional. Max 20 characters.
        city (str): Optional. Max 100 characters.
        country (str): Optional. Max 100 characters.
    """
    class Meta:
        """
        Meta options for CompanySchema.

        - model: The SQLAlchemy model to serialize.
        - load_instance: Deserialize to model instances.
        - include_fk: Include foreign keys.
        - dump_only: Fields to exclude from deserialization.
        - unknown: Raise error on unknown fields.
        """
        model = Company
        load_instance = True
        include_fk = True
        dump_only = ('id', 'created_at', 'updated_at')
        unknown = RAISE

    name = fields.String(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
        ]
    )
    description = fields.String(
        validate=validate.Length(max=200)
    )
    logo_url = fields.URL(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    website = fields.URL(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    phone_number = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=20),
            validate.Regexp(
                r"^\d*$", error="Phone number must contain only digits.")
        ]
    )
    email = fields.Email(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    address = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    postal_code = fields.String(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    city = fields.String(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    country = fields.String(
        allow_none=True,
        validate=validate.Length(max=100)
    )

    @validates('name')
    def validate_name(self, value, **kwargs):
        """
        Ensure the company name is unique.

        Args:
            value (str): The name to validate.

        Raises:
            ValidationError: If a company with the same name already exists.
        """
        _ = kwargs
        company = Company.query.filter_by(name=value).first()
        if company:
            raise ValidationError("Company name must be unique.")
