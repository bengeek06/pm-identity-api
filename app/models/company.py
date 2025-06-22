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
        users (list): Relationship to User objects belonging to the company.
        organizations_units (list): Relationship to OrganizationUnit objects
                belonging to the company.
    """
    __tablename__ = 'company'

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
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
    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    users = db.relationship(
        'User',
        back_populates='company',
        lazy=True
    )
    organizations_units = db.relationship(
        'OrganizationUnit',
        back_populates='company',
        lazy=True
    )

    def __repr__(self):
        return (
            f"<Company {self.name}>"
            f" (ID: {self.id}, Description: {self.description})"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all records from the Company table.

        Returns:
            list: List of all Company objects.
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
            Company: The Company object with the given ID, or None if not
            found.
        """
        try:
            return cls.query.get(company_id)
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving company by ID {company_id}: {e}"
            )
            return None

    @classmethod
    def get_by_name(cls, name):
        """
        Retrieve a Company record by its name.

        Args:
            name (str): Name of the Company entity to retrieve.

        Returns:
            Company: The Company object with the given name, or None if not
            found.
        """
        try:
            return cls.query.filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving company by name {name}: {e}"
            )
            return None

    @classmethod
    def create(cls, name, description=None, logo_url=None, website=None,
               phone_number=None, email=None, address=None, postal_code=None,
               city=None, country=None):
        """
        Create a new Company record.

        Args:
            name (str): Name of the Company entity.
            description (str, optional): Description of the Company entity.
            logo_url (str, optional): URL of the Company's logo.
            website (str, optional): Website URL of the Company.
            phone_number (str, optional): Phone number of the Company.
            email (str, optional): Email address of the Company.
            address (str, optional): Address of the Company.
            postal_code (str, optional): Postal code of the Company.
            city (str, optional): City where the Company is located.
            country (str, optional): Country where the Company is located.

        Returns:
            Company: The created Company object.
        """
        company = cls(
            name=name,
            description=description,
            logo_url=logo_url,
            website=website,
            phone_number=phone_number,
            email=email,
            address=address,
            postal_code=postal_code,
            city=city,
            country=country
        )

        try:
            db.session.add(company)
            db.session.commit()
            return company
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error creating company: {e}")
            return None

    def update(self, name=None, description=None, logo_url=None, website=None,
               phone_number=None, email=None, address=None, postal_code=None,
               city=None, country=None):
        """
        Update the attributes of the Company entity.

        Args:
            name (str, optional): New name for the Company entity.
            description (str, optional): New description for the Company
                                         entity.
            logo_url (str, optional): New URL for the Company's logo.
            website (str, optional): New website URL for the Company.
            phone_number (str, optional): New phone number for the Company.
            email (str, optional): New email address for the Company.
            address (str, optional): New address for the Company.
            postal_code (str, optional): New postal code for the Company.
            city (str, optional): New city for the Company.
            country (str, optional): New country for the Company.
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if logo_url is not None:
            self.logo_url = logo_url
        if website is not None:
            self.website = website
        if phone_number is not None:
            self.phone_number = phone_number
        if email is not None:
            self.email = email
        if address is not None:
            self.address = address
        if postal_code is not None:
            self.postal_code = postal_code
        if city is not None:
            self.city = city
        if country is not None:
            self.country = country

        try:
            db.session.commit()
            return self
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error updating company: {e}")
            return None

    def delete(self):
        """ Delete the Company entity from the database."""
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error deleting company: {e}")
            return False
