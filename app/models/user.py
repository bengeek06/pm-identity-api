"""
Module: user

This module defines the User model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'user' table, including
attributes, relationships, and utility methods for CRUD operations.

The User model represents an individual user account within a company.
"""

import uuid
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash
from app.models import db
from app.logger import logger


class User(db.Model):
    """
    SQLAlchemy model for the 'user' table.

    Represents a user entity in the Identity Service API, including
    its attributes (email, password, profile info, etc.), its relationships
    to company and position, and utility methods for database operations.

    Attributes:
        id (str): Unique identifier (UUID) for the user.
        email (str): Email address of the user (required, unique).
        hashed_password (str): Hashed password for authentication.
        first_name (str): Optional first name of the user.
        last_name (str): Optional last name of the user.
        phone_number (str): Optional phone number of the user.
        avatar_url (str): Optional URL to the user's avatar.
        is_active (bool): Whether the user account is active.
        is_verifed (bool): Whether the user's email is verified.
        last_login_at (datetime): Timestamp of the user's last login.
        company_id (str): Foreign key referencing the associated company.
        position_id (str): Foreign key referencing the user's position.
        created_at (datetime): Timestamp when the user was created.
        updated_at (datetime): Timestamp when the user was last updated.
    """
    __tablename__ = 'user'

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    email = db.Column(db.String(100), nullable=False, unique=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verifed = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    company_id = db.Column(
        db.String(36),
        db.ForeignKey('company.id'),
        nullable=False
    )
    position_id = db.Column(
        db.String(36),
        db.ForeignKey('position.id'),
        nullable=True
    )
    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    company = db.relationship('Company', back_populates='users', lazy=True)

    def __repr__(self):
        return (
            f"<User {self.email}>"
            f" (ID: {self.id}, First Name: {self.first_name}, "
            f"Last Name: {self.last_name}, Company ID: {self.company_id})"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all users from the database.

        Returns:
            list: List of all User objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error("Error retrieving users: %s", str(e))
            return []

    @classmethod
    def get_by_id(cls, user_id):
        """
        Retrieve a user by its ID.

        Args:
            user_id (str): The ID of the user.

        Returns:
            User: The User object if found, None otherwise.
        """
        try:
            return cls.query.get(user_id)
        except SQLAlchemyError as e:
            logger.error("Error retrieving user by ID %s: %s", user_id, str(e))
            return None

    @classmethod
    def get_by_email(cls, email):
        """
        Retrieve a user by their email address.

        Args:
            email (str): The email address of the user.

        Returns:
            User: The User object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(email=email).first()
        except SQLAlchemyError as e:
            logger.error("Error retrieving user by email %s: %s", email, str(e))
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all users associated with a specific company.

        Args:
            company_id (str): Unique identifier of the company.

        Returns:
            list: List of User objects associated with the company.
        """
        try:
            return cls.query.filter_by(company_id=company_id).all()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving users for company %s: %s", company_id, str(e)
            )
            return []

    @classmethod
    def get_by_position_id(cls, position_id):
        """
        Retrieve all users associated with a specific position.

        Args:
            position_id (str): Unique identifier of the position.

        Returns:
            list: List of User objects associated with the position.
        """
        try:
            return cls.query.filter_by(position_id=position_id).all()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving users for position %s: %s", position_id, str(e)
            )
            return []

    @classmethod
    def get_by_name(cls, first_name=None, last_name=None):
        """
        Retrieve users by their first and/or last name.

        Args:
            first_name (str): Optional first name of the user.
            last_name (str): Optional last name of the user.

        Returns:
            list: List of User objects matching the criteria.
        """
        try:
            query = cls.query
            if first_name:
                query = query.filter(cls.first_name.ilike(f"%{first_name}%"))
            if last_name:
                query = query.filter(cls.last_name.ilike(f"%{last_name}%"))
            return query.all()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving users by name: %s", str(e)
            )
            return []

    def verify_password(self, password):
        """
        Verify the user's password.

        Args:
            password (str): The password to verify.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return check_password_hash(self.hashed_password, password)