"""
Module: app.rate_limiter

This module initializes the Flask-Limiter instance for rate limiting.
Separated from __init__.py to avoid circular imports.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Will be overridden by config
)
