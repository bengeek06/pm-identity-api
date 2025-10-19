"""
Module: user

This module defines the User model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'user' table, including
attributes, relationships, and utility methods for CRUD operations.

The User model represents an individual user account within a company.
"""

import os
import uuid
import enum

import requests
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import db
from app.logger import logger


class LanguageEnum(enum.Enum):
    """Enumeration for supported user languages."""

    EN = "en"
    FR = "fr"


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
        language (LanguageEnum): Preferred language of the user.
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

    __tablename__ = "user"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email = db.Column(db.String(100), nullable=False, unique=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    language = db.Column(
        db.Enum(LanguageEnum), default=LanguageEnum.EN, nullable=False
    )
    phone_number = db.Column(db.String(50), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verifed = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    # Allow nullable company_id for superuser creation
    company_id = db.Column(
        db.String(36), db.ForeignKey("company.id"), nullable=True, index=True
    )
    position_id = db.Column(
        db.String(36), db.ForeignKey("position.id"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    company = db.relationship("Company", back_populates="users", lazy=True)

    def __repr__(self):
        """
        Return a string representation of the User instance.

        Returns:
            str: String representation of the user.
        """
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
            list[User]: List of all User objects, or an empty list if an
                        error occurs.
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
            User or None: The User object if found, None otherwise.
        """
        try:
            return db.session.get(cls, user_id)
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
            User or None: The User object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(email=email).first()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving user by email %s: %s", email, str(e)
            )
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all users associated with a specific company.

        Args:
            company_id (str): Unique identifier of the company.

        Returns:
            list[User]: List of User objects associated with the company,
                        or an empty list if an error occurs.
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
            list[User]: List of User objects associated with the position,
                        or an empty list if an error occurs.
        """
        try:
            return cls.query.filter_by(position_id=position_id).all()
        except SQLAlchemyError as e:
            logger.error(
                "Error retrieving users for position %s: %s",
                position_id,
                str(e),
            )
            return []

    @classmethod
    def get_by_name(cls, first_name=None, last_name=None):
        """
        Retrieve users by their first and/or last name.

        Args:
            first_name (str, optional): First name of the user.
            last_name (str, optional): Last name of the user.

        Returns:
            list[User]: List of User objects matching the criteria,
                        or an empty list if an error occurs.
        """
        try:
            query = cls.query
            if first_name:
                query = query.filter(cls.first_name.ilike(f"%{first_name}%"))
            if last_name:
                query = query.filter(cls.last_name.ilike(f"%{last_name}%"))
            return query.all()
        except SQLAlchemyError as e:
            logger.error("Error retrieving users by name: %s", str(e))
            return []

    def verify_password(self, password):
        """
        Verify the user's password against the stored hash.

        Args:
            password (str): The password to verify.

        Returns:
            bool: True if password matches the stored hash, False otherwise.
        """
        return check_password_hash(self.hashed_password, password)

    def is_superuser(self):
        """
        Check if the user is a superuser (no company_id).

        Returns:
            bool: True if user is a superuser, False otherwise.
        """
        return self.company_id is None

    @classmethod
    def get_superusers(cls):
        """
        Retrieve all superusers from the database.

        Returns:
            list[User]: List of superuser User objects, or an empty list if an
                        error occurs.
        """
        try:
            return cls.query.filter(cls.company_id.is_(None)).all()
        except SQLAlchemyError as e:
            logger.error("Error retrieving superusers: %s", str(e))
            return []

    @classmethod
    def ensure_superuser_exists(cls):
        """
        Ensure that at least one superuser exists in the database.

        If the user table is completely empty, create a default superuser
        with a generated UUID and a placeholder password.
        """
        try:
            # Check if the user table is empty
            user_count = cls.query.count()
            if user_count == 0:
                # TODO: Send request to guardian API to get superadmin role ID
                guardian = os.getenv("GUARDIAN_SERVICE_URL")
                response = requests.get(f"{guardian}/roles")
                if response.status_code == 200:
                    roles = response.json()
                    superadmin_role = next(
                        (
                            role
                            for role in roles
                            if role["name"] == "superadmin"
                        ),
                        None,
                    )
                    if not superadmin_role:
                        logger.error(
                            "Superadmin role not found in Guardian API."
                        )
                        return None

                superuser = cls(
                    email="superuser@example.com",
                    first_name="Super",
                    last_name="User",
                    role_id=superadmin_role["id"],
                    hashed_password=generate_password_hash("SuperUser123!"),
                )
                db.session.add(superuser)
                db.session.commit()
                logger.info("Created default superuser (table was empty).")
                return superuser

            logger.info(
                "User table is not empty, no need to create superuser."
            )
            return None
        except Exception as e:
            logger.error("Error creating default superuser: %s", str(e))
            db.session.rollback()
            return None
