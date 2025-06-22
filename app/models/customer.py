"""
Module: customer

This module defines the Customer model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'customer' table, including
attributes, relationships, and utility methods for CRUD operations.

The Customer model represents a client or customer entity associated with a company.
"""

import uuid
from sqlalchemy.exc import SQLAlchemyError
from app.models import db
from app.logger import logger


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
    __tablename__ = 'customer'

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(
        db.String(36),
        db.ForeignKey('company.id'),
        nullable=False)
    email = db.Column(db.String(100), nullable=True, unique=True)
    contact_person = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def __repr__(self):
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
            list: List of all Customer objects.
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
            Customer: The Customer object if found, else None.
        """
        try:
            return cls.query.filter_by(id=customer_id).first()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving customer by ID {customer_id}: {e}"
            )
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all Customer records associated with a specific company.

        Args:
            company_id (str): The ID of the company.
            
        Returns:
            list: List of Customer objects associated with the company.
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
            Customer: The Customer object if found, else None.
        """
        try:
            return cls.query.filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer by name {name}: {e}")
            return None

    @classmethod
    def get_by_email(cls, email):
        """
        Retrieve a Customer record by its email address.

        Args:
            email (str): The email address of the customer.

        Returns:
            Customer: The Customer object if found, else None.
        """
        try:
            return cls.query.filter_by(email=email).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer by email {email}: {e}")
            return None

    @classmethod
    def create(cls, name, company_id, email, contact_person=None,
               phone_number=None, address=None):
        """
        Create a new Customer record.

        Args:
            name (str): The name of the customer.
            company_id (str): The ID of the associated company.
            email (str, optional): The email of the customer.
            contact_person (str, optional): The contact person for the
                                            customer.
            phone_number (str, optional): The phone number of the customer.
            address (str, optional): The address of the customer.
        
        Returns:
            Customer: The newly created Customer object.
        """
        customer = cls(
            name=name,
            company_id=company_id,
            email=email,
            contact_person=contact_person,
            phone_number=phone_number,
            address=address
        )

        try:
            db.session.add(customer)
            db.session.commit()
            return customer
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error creating customer: {e}")
            return None

    def update(self, name=None, email=None, contact_person=None,
               phone_number=None, address=None):
        """
        Update an existing Customer record.

        Args:
            name (str, optional): The new name of the customer.
            email (str, optional): The new email of the customer.
            contact_person (str, optional): The new contact person for the
                                            customer.
            phone_number (str, optional): The new phone number of the
                                          customer.
            address (str, optional): The new address of the customer.
        
        Returns:
            Customer: The updated Customer object.
        """
        if name:
            self.name = name
        if email:
            self.email = email
        if contact_person:
            self.contact_person = contact_person
        if phone_number:
            self.phone_number = phone_number
        if address:
            self.address = address

        try:
            db.session.commit()
            return self
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error updating customer: {e}")
            return None

    def delete(self):
        """
        Delete the Customer record from the database.

        Returns:
            bool: True if deletion was successful, else False.
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error deleting customer: {e}")
            return False
