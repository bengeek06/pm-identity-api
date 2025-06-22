"""
Module: organzation_unit_schema

This module defines the Marshmallow schema for serializing, deserializing,
and validating OrganizationUnit model instances in the Identity Service API.

The OrganizationUnitSchema class provides field validation and metadata for the
OrganizationUnit model, ensuring data integrity and proper formatting when
handling API input and output.
"""

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import ValidationError, validates

from app.models.organization_unit import OrganizationUnit
from app.models.company import Company
from app.logger import logger


class OrganizationUnitSchema(SQLAlchemyAutoSchema):
    """
    Serialization and validation schema for the OrganizationUnit model.

    Attributes:
        id (int): Unique identifier for the OrganizationUnit entity.
        name (str): Name of the OrganizationUnit entity.
        company_id (int): Foreign key to the associated Company entity.
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
        """
        model = OrganizationUnit
        load_instance = True
        include_fk = True
        dump_only = ('id', 'created_at', 'updated_at')

    @validates('name')
    def validate_name(self, value, **kwargs):
        """
        Validate that the name is not empty and is unique.

        Args:
            value (str): The name to validate.

        Raises:
            ValidationError: If the name is empty or already exists.

        Returns:
            str: The validated name.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Name cannot be empty.")
            raise ValidationError("Name cannot be empty.")

        organization_unit = OrganizationUnit.get_by_name(value)
        if organization_unit:
            logger.error("Validation error: Name must be unique.")
            raise ValidationError("Name must be unique.")

        return value

    @validates('company_id')
    def validate_company_id(self, value, **kwargs):
        """
        Validate that the company_id is not empty and exists in the Company model.

        Args:
            value (str): The company_id to validate.

        Raises:
            ValidationError: If the company_id is empty or does not exist.

        Returns:
            str: The validated company_id.
        """
        _ = kwargs

        if not value:
            logger.error("Validation error: Company ID cannot be empty.")
            raise ValidationError("Company ID cannot be empty.")

        company = Company.get_by_id(value)
        if not company:
            logger.error(f"Validation error: Company with ID {value} does not exist.")
            raise ValidationError("Company ID does not exist.")

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
            logger.error("Validation error: Description cannot exceed 200 characters.")
            raise ValidationError("Description cannot exceed 200 characters.")

        return value

    @validates('parent_id')
    def validate_parent_id(self, value, **kwargs):
        """
        Validate that the parent_id is either None or a valid organization unit ID.

        Args:
            value (str): The parent_id to validate.

        Raises:
            ValidationError: If the parent_id does not exist in the OrganizationUnit model.

        Returns:
            str: The validated parent_id.
        """
        _ = kwargs

        if value:
            parent_unit = OrganizationUnit.get_by_id(value)
            if not parent_unit:
                logger.error(f"Validation error: Parent ID {value} does not exist.")
                raise ValidationError("Parent ID does not exist.")

        return value

    @validates('path')
    def validate_path(self, value, **kwargs):
        """
        Validate that the path is a valid hierarchical path format and that
        each organization unit in the path exists and is the parent of the next.

        Args:
            value (str): The path to validate.

        Raises:
            ValidationError: If the path is not valid or the hierarchy is broken.

        Returns:
            str: The validated path.
        """
        _ = kwargs

        if value:
            if not isinstance(value, str):
                logger.error("Validation error: Path must be a string.")
                raise ValidationError("Path must be a string.")

            ids = value.strip("/").split("/")
            prev_unit = None
            for org_id in ids:
                unit = OrganizationUnit.get_by_id(org_id)
                if not unit:
                    logger.error(f"Validation error: Org unit ID {org_id} does not exist in path.")
                    raise ValidationError(f"Org unit ID {org_id} does not exist in path.")
                if prev_unit and unit.parent_id != prev_unit.id:
                    logger.error("Validation error: Path hierarchy is inconsistent.")
                    raise ValidationError("Path hierarchy is inconsistent.")
                prev_unit = unit

        return value

    @validates('level')
    def validate_level(self, value, **kwargs):
        """
        Validate that the level matches the number of parents in the hierarchy.

        Args:
            value (int): The level to validate.

        Raises:
            ValidationError: If the level does not match the number of parents.

        Returns:
            int: The validated level.
        """
        _ = kwargs

        # Retrieve parent_id from the data being validated
        parent_id = self.context.get('parent_id') if hasattr(self, 'context') else None
        # If parent_id is not in context, try to get it from self.instance or kwargs
        if not parent_id and hasattr(self, 'instance') and getattr(self.instance, 'parent_id', None):
            parent_id = self.instance.parent_id

        # Count the number of parents in the hierarchy
        parent_count = 0
        current_id = parent_id
        while current_id:
            parent_unit = OrganizationUnit.get_by_id(current_id)
            if not parent_unit:
                break
            parent_count += 1
            current_id = parent_unit.parent_id

        if value != parent_count:
            logger.error(
                f"Validation error: Level {value} does not match the number of parents {parent_count}."
            )
            raise ValidationError(
                f"Level must match the number of parents in the hierarchy ({parent_count})."
            )

        return value
