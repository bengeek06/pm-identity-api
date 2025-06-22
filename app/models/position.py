"""
Module: position

This module defines the Position model for the Identity Service API.
It provides the SQLAlchemy ORM mapping for the 'position' table, including
attributes, relationships, and utility methods for CRUD operations.

The Position model represents a job position within a company, such as a role
or title.
"""

import uuid
from sqlalchemy.exc import SQLAlchemyError
from app.models import db
from app.logger import logger

class Position(db.Model):
    """
    SQLAlchemy model for the 'position' table.

    Represents a position entity in the Identity Service API, including
    its attributes (title, description, etc.), its relationship to a company,
    and utility methods for database operations.

    Attributes:
        id (str): Unique identifier (UUID) for the position.
        title (str): Title or name of the position (required).
        company_id (str): Foreign key referencing the associated company.
        description (str): Optional description of the position.
        level (int): Optional level or rank of the position.
        created_at (datetime): Timestamp when the position was created.
        updated_at (datetime): Timestamp when the position was last updated.
    """
    __tablename__ = 'position'

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    title = db.Column(db.String(100), nullable=False)
    company_id = db.Column(
        db.String(36),
        db.ForeignKey('company.id'),
        nullable=False)
    description = db.Column(db.String(255), nullable=True)
    level = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def __repr__(self):
        return (
            f"<Position {self.title}>"
            f" (ID: {self.id}, Company ID: {self.company_id})"
        )

    @classmethod
    def get_all(cls):
        """
        Retrieve all positions from the database.

        Returns:
            list: List of Position objects.
        """
        try:
            return cls.query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving positions: {e}")
            return []

    @classmethod
    def get_by_id(cls, position_id):
        """
        Retrieve a position by its ID.

        Args:
            position_id (str): Unique identifier of the position.

        Returns:
            Position: Position object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(id=position_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving position by ID {position_id}: {e}")
            return None

    @classmethod
    def get_by_company_id(cls, company_id):
        """
        Retrieve all positions associated with a specific company.

        Args:
            company_id (str): Unique identifier of the company.

        Returns:
            list: List of Position objects associated with the company.
        """
        try:
            return cls.query.filter_by(company_id=company_id).all()
        except SQLAlchemyError as e:
            logger.error(
                f"Error retrieving positions for company {company_id}: {e}"
            )
            return []

    @classmethod
    def get_by_title(cls, title):
        """
        Retrieve a position by its title.

        Args:
            title (str): Title of the position.

        Returns:
            Position: Position object if found, None otherwise.
        """
        try:
            return cls.query.filter_by(title=title).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving position by title {title}: {e}")
            return None

    @classmethod
    def create(cls, title, company_id, description=None, level=None):
        """
        Create a new position in the database.

        Args:
            title (str): Title of the position (required).
            company_id (str): ID of the associated company (required).
            description (str, optional): Description of the position.
            level (int, optional): Level or rank of the position.

        Returns:
            Position: The created Position object.
        """
        try:
            position = cls(
                title=title,
                company_id=company_id,
                description=description,
                level=level
            )
            db.session.add(position)
            db.session.commit()
            return position
        except SQLAlchemyError as e:
            logger.error(f"Error creating position: {e}")
            db.session.rollback()
            return None

    def update(self, title=None, description=None, level=None):
        """
        Update the attributes of an existing position.

        Args:
            title (str, optional): New title for the position.
            description (str, optional): New description for the position.
            level (int, optional): New level for the position.

        Returns:
            Position: The updated Position object.
        """
        if title:
            self.title = title
        if description:
            self.description = description
        if level is not None:
            self.level = level
        
        try:
            db.session.commit()
            return self
        except SQLAlchemyError as e:
            logger.error(f"Error updating position {self.id}: {e}")
            db.session.rollback()
            return None

    def delete(self):
        """
        Delete the position from the database.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting position {self.id}: {e}")
            db.session.rollback()
            return False
    