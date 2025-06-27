"""
Module imports for the app.resources package.

This module ensures that all SQLAlchemy models are imported and registered,
so that they are available for use throughout the application, including
for database migrations and relationships.
"""

from app.models.user import User
from app.models.organization_unit import OrganizationUnit
from app.models.company import Company
from app.models.position import Position
from app.models.customer import Customer
