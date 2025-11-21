# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Module: app.models.__init__

Initializes the SQLAlchemy instance (db) for the Flask application.
This instance is used throughout the application for ORM operations.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
