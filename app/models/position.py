"""
Module: position

This module defines the Position model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'position' table, including
attributes, relationships, and utility methods for CRUD operations.

The Position model represents a job position within a company, such as a role
or title.
"""

import uuid
from sqlalchemy.exc import SQLAlchemyError
from app.models import db
from app.logger import logger


class Position(db.Model):
    """
    SQLAlchemy model for the 'position' table.

    Represents a position entity in the Identity Service API, including
    its attributes (title, description, etc.), its relationship to a company
    and organization unit, and utility methods for database operations.

    Attributes:
        id (str): Unique identifier (UUID) for the position.
        title (str): Title or name of the position (required).
        company_id (str): Foreign key referencing the associated company.
        organization_unit_id (str): Foreign key referencing the organization
                                    unit.
        description (str): Optional description of the position.
        level (int): Optional level or rank of the position.
        created_at (datetime): Timestamp when the position was created.
        updated_at (datetime): Timestamp when the position was last updated.
    """

    __tablename__ = "position"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    company_id = db.Column(db.String(36), db.ForeignKey("company.id"), nullable=False)
    organization_unit_id = db.Column(
        db.String(36), db.ForeignKey("organization_unit.id"), nullable=False
    )
    description = db.Column(db.String(255), nullable=True)
    level = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    organization_unit = db.relationship(
        "OrganizationUnit", back_populates="positions", lazy=True
    )

    def __repr__(self):
        """
        Return a string representation of the Position instance.

        Returns:
            str: String representation of the position.
        """
        return (
            f"<Position {self.title}>"
            f" (ID: {self.id}, Company ID: {self.company_id})"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all positions from the database.

        Returns:
            list[Position]: List of Position objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving positions: {e}")
            return []

    @classmethod
    def get_by_id(cls, position_id):
        """
        Retrieve a position by its ID.

        Args:
            position_id (str): Unique identifier of the position.

        Returns:
            Position or None: Position object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(id=position_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving position by ID {position_id}: {e}")
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all positions associated with a specific company.

        Args:
            company_id (str): Unique identifier of the company.

        Returns:
            list[Position]: List of Position objects associated with the
                            company.
        """
        try:
            return cls.query.filter_by(company_id=company_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving positions for company {company_id}: {e}")
            return []

    @classmethod
    def get_by_title(cls, title):
        """
        Retrieve a position by its title.

        Args:
            title (str): Title of the position.

        Returns:
            Position or None: Position object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(title=title).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving position by title {title}: {e}")
            return None

    @classmethod
    def get_by_organization_unit_id(cls, organization_unit_id):
        """
        Retrieve all positions associated with a specific organization unit.

        Args:
            organization_unit_id (str): Unique identifier of the organization
                                        unit.

        Returns:
            list[Position]: List of Position objects associated with the
                            organization unit.
        """
        try:
            return cls.query.filter_by(organization_unit_id=organization_unit_id).all()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving positions for organization unit %s: %s",
                organization_unit_id,
                e,
            )
            return []
