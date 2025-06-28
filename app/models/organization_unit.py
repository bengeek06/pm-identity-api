"""
Module: organization_unit

This module defines the OrganizationUnit model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'organization_unit' table,
including attributes, relationships, and utility methods for CRUD operations.

The OrganizationUnit model represents a structural unit within a company, such
as a department or division.
"""

import uuid
from sqlalchemy.exc import SQLAlchemyError
from app.models import db
from app.logger import logger


class OrganizationUnit(db.Model):
    """
    SQLAlchemy model for the 'organization_unit' table.

    Represents an organization unit entity in the Identity Service API,
    including its attributes (name, description, etc.), its relationship to a
    company, and utility methods for database operations.

    Attributes:
        id (str): Unique identifier (UUID) for the organization unit.
        name (str): Name of the organization unit (required).
        company_id (str): Foreign key referencing the associated company.
        description (str): Optional description of the organization unit.
        parent_id (str): Optional foreign key referencing the parent
                         organization unit.
        path (str): Optional hierarchical path of the organization unit.
        level (int): Optional level in the organization hierarchy.
        created_at (datetime): Timestamp when the organization unit was
                               created.
        updated_at (datetime): Timestamp when the organization unit was last
                               updated.
    """
    __tablename__ = 'organization_unit'

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(
        db.String(36),
        db.ForeignKey('company.id'),
        nullable=False
    )
    description = db.Column(db.String(255), nullable=True)
    parent_id = db.Column(
        db.String(36),
        db.ForeignKey('organization_unit.id'),
        nullable=True
    )
    path = db.Column(db.String(255), nullable=True)
    level = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )
    company = db.relationship(
        'Company',
        back_populates='organizations_units',
        lazy=True
    )
    positions = db.relationship(
        'Position',
        back_populates='organization_unit',
        cascade='all, delete-orphan',
        lazy=True
    )

    def __repr__(self):
        return (
            f"<OrganizationUnit {self.name} (ID: {self.id})>, "
            f"Company ID: {self.company_id}"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all organization units from the database.

        Returns:
            list: List of all OrganizationUnit objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving organization units: {e}")
            return []

    @classmethod
    def get_by_id(cls, unit_id):
        """
        Retrieve an organization unit by its ID.

        Args:
            unit_id (str): The ID of the organization unit.

        Returns:
            OrganizationUnit: The OrganizationUnit object if found, else None.
        """
        try:
            return cls.query.filter_by(id=unit_id).first()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving organization unit by ID {unit_id}: {e}")
            return None

    @classmethod
    def get_by_name(cls, name):
        """
        Retrieve an organization unit by its name.

        Args:
            name (str): The name of the organization unit.

        Returns:
            OrganizationUnit: The OrganizationUnit object if found, else None.
        """
        try:
            return cls.query.filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving organization unit by name {name}: {e}")
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all organization units associated with a specific company.

        Args:
            company_id (str): The ID of the company.

        Returns:
            list: List of OrganizationUnit objects associated with the company.
        """
        try:
            return cls.query.filter_by(company_id=company_id).all()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving org units for company ID {company_id}: {e}"
            )
            return []

    @classmethod
    def get_children(cls, parent_id):
        """
        Retrieve all child organization units of a given parent unit.

        Args:
            parent_id (str): The ID of the parent organization unit.

        Returns:
            list: List of OrganizationUnit objects that are children of the
                  specified parent.
        """
        try:
            return cls.query.filter_by(parent_id=parent_id).all()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving children for parent ID %s: %s", parent_id, e
            )
            return []

    def update_path_and_level(self):
        """
        Update the 'path' and 'level' fields based on the parent_id.
        Should be called after setting/changing parent_id and before commit.
        """
        if self.parent_id:
            parent = OrganizationUnit.get_by_id(self.parent_id)
            if parent:
                self.path = f"{parent.path or parent.id}/{self.id}"
                self.level = (parent.level or 0) + 1
            else:
                self.path = str(self.id)
                self.level = 0
        else:
            self.path = str(self.id)
            self.level = 0
