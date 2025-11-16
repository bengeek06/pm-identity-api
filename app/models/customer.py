"""
Module: customer

This module defines the Customer model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'customer' table, including
attributes, relationships, and utility methods for CRUD operations.

The Customer model represents a client or customer entity associated with a
company.
"""

import uuid

from sqlalchemy.exc import SQLAlchemyError

from app.logger import logger
from app.models import db


class Customer(db.Model):
    """
    SQLAlchemy model for the 'customer' table.

    Represents a customer entity in the Identity Service API, including
    its attributes (name, contact info, etc.), its relationship to a company,
    and utility methods for database operations.

    Attributes:
        id (str): Unique identifier (UUID) for the customer.
        name (str): Name of the customer (required).
        company_id (str): Foreign key referencing the associated company.
        email (str): Optional email address of the customer (unique).
        contact_person (str): Optional contact person for the customer.
        phone_number (str): Optional phone number of the customer.
        address (str): Optional address of the customer.
        created_at (datetime): Timestamp when the customer was created.
        updated_at (datetime): Timestamp when the customer was last updated.
    """

    __tablename__ = "customer"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(
        db.String(36), db.ForeignKey("company.id"), nullable=False
    )
    email = db.Column(db.String(100), nullable=True, unique=True)
    contact_person = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    def __repr__(self):
        """
        Return a string representation of the Customer instance.

        Returns:
            str: String representation of the customer.
        """
        return (
            f"<Customer {self.name}>"
            f" (ID: {self.id}, Email: {self.email}), "
            f" Company ID: {self.company_id}"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all records from the Customer table.

        Returns:
            list[Customer]: List of all Customer objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customers: {e}")
            return []

    @classmethod
    def get_by_id(cls, customer_id):
        """
        Retrieve a Customer record by its ID.

        Args:
            customer_id (str): The ID of the customer.

        Returns:
            Customer or None: The Customer object if found, else None.
        """
        try:
            return cls.query.filter_by(id=customer_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer by ID {customer_id}: {e}")
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all Customer records associated with a specific company.

        Args:
            company_id (str): The ID of the company.

        Returns:
            list[Customer]: List of Customer objects associated with the
                            company.
        """
        try:
            return cls.query.filter_by(company_id=company_id).all()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving customers by company ID {company_id}: {e}"
            )
            return []

    @classmethod
    def get_by_name(cls, name):
        """
        Retrieve a Customer record by its name.

        Args:
            name (str): The name of the customer.

        Returns:
            Customer or None: The Customer object if found, else None.
        """
        try:
            return cls.query.filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer by name {name}: {e}")
            return None
