# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Module: user

This module defines the User model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'user' table, including
attributes, relationships, and utility methods for CRUD operations.

The User model represents an individual user account within a company.
"""

import enum
import uuid

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

from app.logger import logger
from app.models import db


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
        avatar_file_id (str): Storage Service file_id reference for avatar.
        has_avatar (bool): Whether the user has an avatar uploaded.
        is_active (bool): Whether the user account is active.
        is_verified (bool): Whether the user's email is verified.
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
    avatar_file_id = db.Column(db.String(36), nullable=True)
    has_avatar = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verifed = db.Column("is_verified", db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    company_id = db.Column(
        db.String(36), db.ForeignKey("company.id"), nullable=False, index=True
    )
    position_id = db.Column(
        db.String(36), db.ForeignKey("position.id"), nullable=True
    )
    # Password reset fields (Issue #12 Phase 1)
    password_reset_required = db.Column(
        db.Boolean, default=False, nullable=False
    )
    last_password_change = db.Column(db.DateTime, nullable=True)
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

    def set_avatar(self, file_id: str) -> None:
        """
        Set user avatar file_id and flag.

        Args:
            file_id (str): Storage Service file_id for the avatar.
        """
        self.avatar_file_id = file_id
        self.has_avatar = True

    def remove_avatar(self) -> None:
        """Clear user avatar reference and flag."""
        self.avatar_file_id = None
        self.has_avatar = False

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
