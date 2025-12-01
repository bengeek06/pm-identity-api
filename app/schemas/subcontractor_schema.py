# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
subcontractor_schema.py
-----------------------

This module defines the Marshmallow schema for serializing, deserializing,
and validating Subcontractor model instances in the Identity Service API.

The SubcontractorSchema class provides field validation and metadata for the
Subcontractor model, ensuring data integrity and proper formatting when
handling API input and output.
"""

from marshmallow import RAISE, ValidationError, fields, validate, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.logger import logger
from app.models.subcontractor import Subcontractor


class SubcontractorSchema(SQLAlchemyAutoSchema):
    """
    Marshmallow schema for the Subcontractor model.

    This schema serializes and validates Subcontractor objects, enforcing field
    types, length constraints, and format (UUID, email, phone, etc.). It also
    ensures proper deserialization and serialization for API input/output.

    Fields:
        id (str): Unique identifier for the Subcontractor entity.
        name (str): Name of the subcontractor.
        description (str): Description of the subcontractor.
        company_id (str): Foreign key to the associated company (UUID).
        contact_person (str): Optional contact person for the subcontractor.
        phone_number (str): Optional phone number. International format allowed
            (digits, +, spaces, (), -), max 50 characters.
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
        dump_only = (
            "id",
            "created_at",
            "updated_at",
            "company_id",
            "logo_file_id",
            "has_logo",
        )
        unknown = RAISE

    name = fields.String(
        required=True,
        validate=validate.Length(
            min=1, max=100, error="Name must be between 1 and 100 characters."
        ),
    )

    description = fields.String(
        required=False,
        validate=validate.Length(
            max=255, error="Description cannot exceed 255 characters."
        ),
    )

    contact_person = fields.String(
        required=False,
        validate=validate.Length(
            max=100, error="Contact person cannot exceed 100 characters."
        ),
    )

    phone_number = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=50),
            validate.Regexp(
                r"^[\d\s+()-]*$",
                error="Phone number can only contain digits, spaces, +, (), and -",
            ),
        ],
    )

    email = fields.Email(
        required=False,
        validate=validate.Length(
            max=100, error="Email cannot exceed 100 characters."
        ),
    )

    address = fields.String(
        required=False,
        validate=validate.Length(
            max=200, error="Address cannot exceed 200 characters."
        ),
    )

    @validates("name")
    def validate_name(self, value, **kwargs):
        """
        Validate that the name is not empty and is unique.

        Args:
            value (str): The name to validate.

        Raises:
            ValidationError: If the name already exists for another subcontractor.

        Returns:
            str: The validated name.
        """
        _ = kwargs

        subcontractor = Subcontractor.get_by_name(value)
        current_subcontractor = (
            self.context.get("subcontractor")
            if hasattr(self, "context")
            else None
        )
        if subcontractor and (
            not current_subcontractor
            or subcontractor.id != getattr(current_subcontractor, "id", None)
        ):
            logger.error(
                "Validation error: Subcontractor with name '%s' already exists.",
                value,
            )
            raise ValidationError("Name must be unique.")
        return value
