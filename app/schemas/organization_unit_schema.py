"""
organization_unit_schema.py
---------------------------

This module defines the Marshmallow schema for serializing, deserializing,
and validating OrganizationUnit model instances in the Identity Service API.

The OrganizationUnitSchema class provides field validation and metadata for the
OrganizationUnit model, ensuring data integrity and proper formatting when
handling API input and output.
"""

from typing import Any, Dict
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import RAISE, fields, validate, validates, ValidationError

from app.models.organization_unit import OrganizationUnit


class OrganizationUnitSchema(SQLAlchemyAutoSchema):
    """
    Marshmallow schema for the OrganizationUnit model.

    This schema serializes and validates OrganizationUnit objects, enforcing
    field types, length constraints, and format. It also ensures proper
    deserialization and serialization for API input/output, and prevents
    cycles in the organization hierarchy.

    Fields:
        id (str): Unique identifier for the OrganizationUnit entity.
        name (str): Name of the OrganizationUnit entity.
        company_id (str): Foreign key to the associated Company entity.
        description (str): Optional description of the organization unit.
        parent_id (str): Optional foreign key referencing the parent
                         organization unit.
        path (str): Optional hierarchical path of the organization unit.
        level (int): Optional level in the organization hierarchy.
    """

    class Meta:
        """
        Meta options for the OrganizationUnit schema.

        Attributes:
            model: The SQLAlchemy model associated with this schema.
            load_instance: Whether to load model instances.
            include_fk: Whether to include foreign keys.
            dump_only: Fields that are only used for serialization.
            unknown: How to handle unknown fields during deserialization.
        """

        model = OrganizationUnit
        load_instance = True
        include_fk = True
        dump_only = ("id", "created_at", "updated_at", "path", "level")
        unknown = RAISE

    name = fields.String(
        required=True,
        validate=[
            validate.Length(
                min=1,
                max=100,
                error="Name must be between 1 and 100 characters.",
            ),
            validate.Regexp(
                r"^[a-zA-Z0-9\s\-_.]+$",
                error="Name: only letters, numbers, spaces, -, _ and . allowed.",
            ),
        ],
    )

    company_id = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Company ID cannot be empty."),
    )

    description = fields.String(
        allow_none=True,
        validate=validate.Length(
            max=200, error="Description cannot exceed 200 characters."
        ),
    )

    parent_id = fields.String(
        allow_none=True,
        validate=validate.Regexp(
            r"^[a-fA-F0-9]{8}-"
            r"[a-fA-F0-9]{4}-"
            r"[a-fA-F0-9]{4}-"
            r"[a-fA-F0-9]{4}-"
            r"[a-fA-F0-9]{12}$",
            error="Parent ID must be a valid UUID.",
        ),
    )

    path = fields.String(dump_only=True)
    level = fields.Integer(dump_only=True)

    context: Dict[str, Any]

    @validates("parent_id")
    def validate_parent_id(self, value, **kwargs):
        """
        Validate the parent_id field to prevent self-referencing and cycles.

        Args:
            value (str): The parent_id value to validate.

        Raises:
            ValidationError: If the parent_id is invalid, self-referencing, or
                             creates a cycle.
        """
        _ = kwargs  # Unused, but required for the method signature
        if value is None:
            return
        # Prevent a node from being its own parent
        context = getattr(self, "context", {}) or {}
        if context.get("current_id") and value == context["current_id"]:
            raise ValidationError(
                "An organization unit cannot be its own parent."
            )

        # Prevent cycles (parent_id must not be a descendant)
        current_id = context.get("current_id")
        if current_id:
            parent = OrganizationUnit.get_by_id(value)
            while parent:
                if parent.id == current_id:
                    raise ValidationError(
                        "Can't set parent_id to a descendant (cycle detected)."
                    )
                parent = (
                    OrganizationUnit.get_by_id(parent.parent_id)
                    if parent.parent_id
                    else None
                )
