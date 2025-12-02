# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
company_schema.py
-----------------

Schema definition for the Company model using Marshmallow.

This module provides the CompanySchema class, which serializes and validates
Company objects for API input/output. It enforces field types, length
constraints, formats (email, URL, digits), and ensures the uniqueness of the
company name.
"""

from marshmallow import RAISE, ValidationError, fields, validate, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.models.company import Company


class CompanySchema(SQLAlchemyAutoSchema):
    """
    Marshmallow schema for the Company model.

    This schema serializes and validates Company objects, enforcing field
    types, length constraints, and format (email, URL, digits). It also ensures
    the uniqueness of the company name via a custom validator.

    Fields:
        name (str): Required. 1-100 characters.
        description (str): Optional. Max 200 characters.
        logo_file_id (str): Optional. UUID from Storage Service (dump_only).
        has_logo (bool): Whether company has logo (dump_only).
        website (str): Optional. Must be a valid URL, max 255 characters.
        phone_number (str): Optional. Digits only, max 20 characters.
        email (str): Optional. Must be a valid email, max 255 characters.
        address (str): Optional. Max 255 characters.
        postal_code (str): Optional. Max 20 characters.
        city (str): Optional. Max 100 characters.
        country (str): Optional. Max 100 characters.
    """

    # Permet le passage explicite du contexte lors de l'instanciation
    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop("context", {})
        super().__init__(*args, **kwargs)

    class Meta:
        """
        Meta options for CompanySchema.

        Attributes:
            model: The SQLAlchemy model to serialize.
            load_instance: Deserialize to model instances.
            include_fk: Include foreign keys.
            dump_only: Fields to exclude from deserialization.
            unknown: Raise error on unknown fields.
        """

        model = Company
        load_instance = True
        include_fk = True
        dump_only = (
            "id",
            "created_at",
            "updated_at",
            "logo_file_id",
            "has_logo",
        )
        unknown = RAISE

    name = fields.String(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
        ],
    )
    description = fields.String(validate=validate.Length(max=255))
    logo_file_id = fields.String(dump_only=True, allow_none=True)
    has_logo = fields.Boolean(
        load_default=False, dump_default=False, dump_only=True
    )
    website = fields.URL(allow_none=True, validate=validate.Length(max=255))
    phone_number = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=20),
            validate.Regexp(
                r"^\d*$", error="Phone number must contain only digits."
            ),
        ],
    )
    email = fields.Email(allow_none=True, validate=validate.Length(max=255))
    address = fields.String(allow_none=True, validate=validate.Length(max=255))
    postal_code = fields.String(
        allow_none=True, validate=validate.Length(max=20)
    )
    city = fields.String(allow_none=True, validate=validate.Length(max=100))
    country = fields.String(allow_none=True, validate=validate.Length(max=100))

    @validates("name")
    def validate_name(self, value, **kwargs):
        """
        Ensure the company name is unique, sauf pour la société courante (update).

        Args:
            value (str): The name to validate.

        Raises:
            ValidationError: If a company with the same name already exists for another company.
        """
        _ = kwargs
        company = Company.query.filter_by(name=value).first()
        current_company = (
            self.context.get("company") if hasattr(self, "context") else None
        )
        if company and (
            not current_company
            or company.id != getattr(current_company, "id", None)
        ):
            raise ValidationError("Company name must be unique.")
