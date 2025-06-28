"""
app.resources.__init__
----------------------

This module initializes the app.resources package.

It ensures that all SQLAlchemy models are imported and registered, so that they
are available for use throughout the application, including for database
migrations, relationships, and resource definitions.
"""

from app.models.user import User
from app.models.organization_unit import OrganizationUnit
from app.models.company import Company
from app.models.position import Position
from app.models.customer import Customer
