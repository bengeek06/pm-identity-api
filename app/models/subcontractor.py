"""
Module: subcontractor

This module defines the Subcontractor model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'subcontractor' table, including
attributes, relationships, and utility methods for CRUD operations.

The Subcontractor model represents a subcontractor entity associated with a
company.
"""

import uuid

from sqlalchemy.exc import SQLAlchemyError

from app.logger import logger
from app.models import db


class Subcontractor(db.Model):
    """
    SQLAlchemy model for the 'subcontractor' table.

    Represents a subcontractor entity in the Identity Service API, including
    its attributes (name, contact info, etc.), its relationship to a company,
    and utility methods for database operations.

    Attributes:
        id (str): Unique identifier (UUID) for the subcontractor.
        name (str): Name of the subcontractor (required).
        company_id (str): Foreign key referencing the associated company.
        description (str): Optional description of the subcontractor.
        contact_person (str): Optional contact person for the subcontractor.
        phone_number (str): Optional phone number of the subcontractor.
        email (str): Optional email address of the subcontractor.
        address (str): Optional address of the subcontractor.
        created_at (datetime): Timestamp when the subcontractor was created.
        updated_at (datetime): Timestamp when the subcontractor was last
                               updated.
    """

    __tablename__ = "subcontractor"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(
        db.String(36), db.ForeignKey("company.id"), nullable=False
    )
    description = db.Column(db.String(255), nullable=True)
    contact_person = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    def __repr__(self):
        """
        Return a string representation of the Subcontractor instance.

        Returns:
            str: String representation of the subcontractor.
        """
        return (
            f"<Subcontractor {self.name}>"
            f" (ID: {self.id}, Company ID: {self.company_id})"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all subcontractors from the database.

        Returns:
            list[Subcontractor]: List of Subcontractor objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error("Error retrieving subcontractors: %s", e)
            return []

    @classmethod
    def get_by_id(cls, subcontractor_id):
        """
        Retrieve a subcontractor by its ID.

        Args:
            subcontractor_id (str): The ID of the subcontractor.

        Returns:
            Subcontractor or None: The Subcontractor object if found,
                                   None otherwise.
        """
        try:
            return cls.query.filter_by(id=subcontractor_id).first()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving subcontractor by ID %s: %s",
                subcontractor_id,
                e,
            )
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all subcontractors associated with a specific company.

        Args:
            company_id (str): Unique identifier of the company.

        Returns:
            list[Subcontractor]: List of Subcontractor objects associated
                                 with the company.
        """
        try:
            return cls.query.filter_by(company_id=company_id).all()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving subcontractors by company ID %s: %s",
                company_id,
                e,
            )
            return []

    @classmethod
    def get_by_name(cls, name):
        """
        Retrieve a subcontractor by its name.

        Args:
            name (str): The name of the subcontractor.

        Returns:
            Subcontractor or None: The Subcontractor object if found,
                                   None otherwise.
        """
        try:
            return cls.query.filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving subcontractor by name %s: %s", name, e
            )
            return None
