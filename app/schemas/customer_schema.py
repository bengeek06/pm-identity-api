"""
Module: customer_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating Customer model instances in the Identity Service API.

The CustomerSchema class provides field validation and metadata for the Customer
model, ensuring data integrity and proper formatting when handling API input
and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, validate, RAISE

from app.models.customer import Customer

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
            unknown: Raise error on unknown fields.
        """
        model = Customer
        load_instance = True
        include_fk = True
        dump_only = ('id', 'created_at', 'updated_at')
        unknown = RAISE

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100)
    )

    company_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
    )

    email = fields.Email(
        allow_none=True,
        validate=validate.Length(max=100)
    )

    contact_person = fields.String(
        allow_none=True,
        validate=validate.Length(max=100)
    )

    phone_number = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=50),
            validate.Regexp(
                r"^\d*$", error="Phone number must contain only digits.")
        ]
    )

    address = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )

