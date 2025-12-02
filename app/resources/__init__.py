# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
app.resources.__init__
----------------------

This module initializes the app.resources package.

It ensures that all SQLAlchemy models are imported and registered, so that they
are available for use throughout the application, including for database
migrations, relationships, and resource definitions.
"""

from app.models.company import Company
from app.models.customer import Customer
from app.models.organization_unit import OrganizationUnit
from app.models.position import Position
from app.models.user import User
