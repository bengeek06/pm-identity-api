"""
Module: company

This module defines the Company model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'company' table, including
attributes, relationships, and utility methods for CRUD operations.

The Company model represents an organization or business entity within the
system.
"""

import uuid
from sqlalchemy.exc import SQLAlchemyError
from app.models import db
from app.logger import logger


class Company(db.Model):
    """
    SQLAlchemy model for the 'company' table.

    Represents a company entity in the Identity Service API, including
    its attributes (name, description, contact info, etc.), relationships
    to users and organization units, and utility methods for database
    operations.

    Attributes:
        id (str): Unique identifier (UUID) for the company.
        name (str): Name of the company (required).
        description (str): Optional description of the company.
        logo_url (str): Optional URL to the company's logo.
        website (str): Optional website URL of the company.
        phone_number (str): Optional phone number of the company.
        email (str): Optional email address of the company.
        address (str): Optional address of the company.
        postal_code (str): Optional postal code of the company.
        city (str): Optional city where the company is located.
        country (str): Optional country where the company is located.
        created_at (datetime): Timestamp when the company was created.
        updated_at (datetime): Timestamp when the company was last updated.
        users (list[User]): Relationship to User objects belonging to the
                            company.
        organizations_units (list[OrganizationUnit]): Relationship to
                    OrganizationUnit objects belonging to the company.
    """

    __tablename__ = "company"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    users = db.relationship("User", back_populates="company", lazy=True)
    organizations_units = db.relationship(
        "OrganizationUnit", back_populates="company", lazy=True
    )

    def __repr__(self):
        """
        Return a string representation of the Company instance.

        Returns:
            str: String representation of the company.
        """
        return (
            f"<Company {self.name}>"
            f" (ID: {self.id}, Description: {self.description})"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all records from the Company table.

        Returns:
            list[Company]: List of all Company objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving companies: {e}")
            return []

    @classmethod
    def get_by_id(cls, company_id):
        """
        Retrieve a Company record by its ID.

        Args:
            company_id (str): ID of the Company entity to retrieve.

        Returns:
            Company or None: The Company object with the given ID, or None
                             if not found.
        """
        try:
            return db.session.get(cls, company_id)
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving company by ID {company_id}: {e}")
            return None

    @classmethod
    def get_by_name(cls, name):
        """
        Retrieve a Company record by its name.

        Args:
            name (str): Name of the Company entity to retrieve.

        Returns:
            Company or None: The Company object with the given name, or None
                             if not found.
        """
        try:
            return cls.query.filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving company by name {name}: {e}")
            return None
