"""
Module: position_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating Position model instances in the Identity Service API.

The PositionSchema class provides field validation and metadata for the Position
model, ensuring data integrity and proper formatting when handling API input
and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, validate

from app.models.position import Position


class PositionSchema(SQLAlchemyAutoSchema):
    """
    Serialization and validation schema for the Position model.

    Attributes:
        id (int): Unique identifier for the Position entity.
        title (str): Title of the position.
        description (str): Description of the position.
        company_id (str): Foreign key to the associated company.
        unit_id (str): Foreign key to the associated unit.
        level (int): Level of the position.
    """
    class Meta:
        """
        Meta options for the Position schema.

        Attributes:
            model: The SQLAlchemy model associated with this schema.
            load_instance: Whether to load model instances.
            include_fk: Whether to include foreign keys.
            dump_only: Fields that are only used for serialization.
        """
        model = Position
        load_instance = True
        include_fk = True
        dump_only = ('id', 'created_at', 'updated_at')

    title = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Title cannot be empty.")
    )

    description = fields.String(
        validate=validate.Length(max=200, error="Description cannot exceed 200 characters.")
    )

    company_id = fields.String(
        required=True,
        validate=validate.Regexp(
            r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
            error="Parent ID must be a valid UUID."
        )
    )

    organization_unit_id = fields.String(
    required=True,
    validate=validate.Regexp(
        r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
        error="Organization Unit ID must be a valid UUID."
    )
)

    level = fields.Integer(
        required=False,
        validate=validate.Range(min=0, error="Level must be a positive integer.")
    )
