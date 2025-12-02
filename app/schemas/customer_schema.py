"""
customer_schema.py
------------------

This module defines the Marshmallow schema for serializing, deserializing,
and validating Customer model instances in the Identity Service API.

The CustomerSchema class provides field validation and metadata for the
Customer model, ensuring data integrity and proper formatting when handling API
input and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, validate, RAISE

from app.models.customer import Customer


class CustomerSchema(SQLAlchemyAutoSchema):
    """
    Marshmallow schema for the Customer model.

    This schema serializes and validates Customer objects, enforcing field
    types, length constraints, and format (email, digits). It also ensures
    proper deserialization and serialization for API input/output.

    Fields:
        name (str): Required. 1-100 characters.
        company_id (str): Required. Must be a valid UUID (36 characters).
        email (str): Optional. Must be a valid email, max 100 characters.
        contact_person (str): Optional. Max 100 characters.
        phone_number (str): Optional. Digits only, max 50 characters.
        address (str): Optional. Max 255 characters.
    """

    class Meta:
        """
        Meta options for the Customer schema.

        Attributes:
            model: The SQLAlchemy model associated with this schema.
            load_instance: Whether to load model instances.
            include_fk: Whether to include foreign keys.
            dump_only: Fields that are only used for serialization.
            unknown: Raise error on unknown fields.
        """

        model = Customer
        load_instance = True
        include_fk = True
        dump_only = ("id", "created_at", "updated_at")
        unknown = RAISE

    name = fields.String(required=True, validate=validate.Length(min=1, max=100))

    company_id = fields.String(
        required=True,
        validate=validate.Length(equal=36),
    )

    email = fields.Email(allow_none=True, validate=validate.Length(max=100))

    contact_person = fields.String(allow_none=True, validate=validate.Length(max=100))

    phone_number = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=50),
            validate.Regexp(r"^\d*$", error="Phone number must contain only digits."),
        ],
    )

    address = fields.String(allow_none=True, validate=validate.Length(max=255))
