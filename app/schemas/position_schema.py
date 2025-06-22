"""
Module: position_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating Position model instances in the Identity Service API.

The PositionSchema class provides field validation and metadata for the Position
model, ensuring data integrity and proper formatting when handling API input
and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validates

from app.models.position import Position
from app.models.company import Company
from app.logger import logger


class PositionSchema(SQLAlchemyAutoSchema):
    """
    Serialization and validation schema for the Position model.

    Attributes:
        id (int): Unique identifier for the Position entity.
        title (str): Title of the position.
        description (str): Description of the position.
        company_id (int): Foreign key to the associated company.
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


    @validates('title')
    def validate_title(self, value, **kwargs):
        """
        Validate that the title is not empty and is unique.

        Args:
            value (str): The title to validate.

        Raises:
            ValidationError: If the title is empty or already exists.

        Returns:
            str: The validated title.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Title cannot be empty.")
            raise ValidationError("Title cannot be empty.")
        position = Position.get_by_title(value)
        if position:
            logger.error(
               "Validation error: Position with title '{value}' already exists."
            )
            raise ValidationError(
                f"Position with title '{value}' already exists."
            )
        return value

    @validates('company_id')
    def validate_company_id(self, value, **kwargs):
        """
        Validate that the company_id is not empty and corresponds to an
        existing company.

        Args:
            value (int): The company_id to validate.

        Raises:
            ValidationError: If the company_id is empty or does not exist.

        Returns:
            int: The validated company_id.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Company ID cannot be empty.")
            raise ValidationError("Company ID cannot be empty.")
        company = Company().get_by_id(value)
        if not company:
            logger.error(
                f"Validation error: Company with ID {value} does not exist."
            )
            raise ValidationError(f"Company with ID {value} does not exist.")
        return value

    @validates('description')
    def validate_description(self, value, **kwargs):
        """
        Validate that the description does not exceed 200 characters.

        Args:
            value (str): The description to validate.

        Raises:
            ValidationError: If the description exceeds 200 characters.

        Returns:
            str: The validated description.
        """
        _ = kwargs

        if value and len(value) > 200:
            logger.error(
                "Validation error: Description cannot exceed 200 characters."
            )
            raise ValidationError("Description cannot exceed 200 characters.")
        return value

    @validates('level')
    def validate_level(self, value, **kwargs):
        """
        Validate that the level is a positive integer.

        Args:
            value (int): The level to validate.

        Raises:
            ValidationError: If the level is not a positive integer.

        Returns:
            int: The validated level.
        """
        _ = kwargs

        if value is not None and (not isinstance(value, int) or value < 0):
            logger.error("Validation error: Level must be a positive integer.")
            raise ValidationError("Level must be a positive integer.")
        return value
