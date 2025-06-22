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
from app.models import db
from app.logger import logger

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
    __tablename__ = 'position'

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
    contact_person = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def __repr__(self):
        return (
            f"<Position {self.name}>"
            f" (ID: {self.id}, Company ID: {self.company_id})"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all subcontractors from the database.

        Returns:
            list: List of Position objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving subcontractors: {e}")
            return []

    @classmethod
    def get_by_id(cls, subcontractor_id):
        """
        Retrieve a subcontractor by its ID.

        Args:
            subcontractor_id (str): The ID of the subcontractor.

        Returns:
            Subcontractor: The Subcontractor object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(id=subcontractor_id).first()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving subcontractor by ID {subcontractor_id}: {e}"
            )
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all subcontractors associated with a specific company.

        Args:
            company_id (str): Unique identifier of the company.

        Returns:
            list: List of Subcontractor objects associated with the company.
        """
        try:
            return cls.query.filter_by(company_id=company_id).all()
        except SQLAlchemyError as e:
            logger.error(
              f"Error retrieving subcontractors by company ID {company_id}: {e}"
            )
            return []

    @classmethod
    def get_by_name(cls, name):
        """
        Retrieve a subcontractor by its name.

        Args:
            name (str): The name of the subcontractor.

        Returns:
            Subcontractor: The Subcontractor object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving subcontractor by name {name}: {e}"
            )
            return None

    @classmethod
    def create(cls, name, company_id, description=None,
               contact_person=None, phone_number=None, email=None,
               address=None):
        """
        Create a new subcontractor record.

        Args:
            name (str): Name of the subcontractor.
            company_id (str): ID of the associated company.
            description (str, optional): Description of the subcontractor.
            contact_person (str, optional): Contact person for the
                                            subcontractor.
            phone_number (str, optional): Phone number of the subcontractor.
            email (str, optional): Email address of the subcontractor.
            address (str, optional): Address of the subcontractor.

        Returns:
            Subcontractor: The created Subcontractor object.
        """
        try:
            subcontractor = cls(
                name=name,
                company_id=company_id,
                description=description,
                contact_person=contact_person,
                phone_number=phone_number,
                email=email,
                address=address
            )
            db.session.add(subcontractor)
            db.session.commit()
            return subcontractor
        except SQLAlchemyError as e:
            logger.error(f"Error creating subcontractor: {e}")
            db.session.rollback()
            return None

    def update(self, name=None, description=None,
               contact_person=None, phone_number=None, email=None,
               address=None):
        """
        Update an existing subcontractor record.

        Args:
            name (str, optional): New name of the subcontractor.
            description (str, optional): New description of the subcontractor.
            contact_person (str, optional): New contact person for the
                                            subcontractor.
            phone_number (str, optional): New phone number of the
                                          subcontractor.
            email (str, optional): New email address of the subcontractor.
            address (str, optional): New address of the subcontractor.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        if name:
            self.name = name
        if description:
            self.description = description
        if contact_person:
            self.contact_person = contact_person
        if phone_number:
            self.phone_number = phone_number
        if email:
            self.email = email
        if address:
            self.address = address

        try:
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating subcontractor: {e}")
            db.session.rollback()
            return False

    def delete(self):
        """
        Delete the subcontractor record from the database.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting subcontractor {self.id}: {e}")
            db.session.rollback()
            return False
