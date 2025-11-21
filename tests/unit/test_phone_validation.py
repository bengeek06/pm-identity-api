# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
test_phone_validation.py
------------------------

This module contains tests for phone number validation in Customer and
Subcontractor schemas, ensuring international formats are accepted.
"""

import pytest
from marshmallow import ValidationError

from app.models import db
from app.schemas.customer_schema import CustomerSchema
from app.schemas.subcontractor_schema import SubcontractorSchema


def test_customer_phone_number_valid_formats(app):
    """Test that various international phone number formats are accepted."""
    valid_phones = [
        "0123456789",  # Digits only
        "+33 1 23 45 67 89",  # International with spaces
        "(555) 123-4567",  # US format with parentheses
        "+1-555-123-4567",  # International with dashes
        "01-23-45-67-89",  # French with dashes
        "+1 (555) 123-4567",  # International + US format
        "",  # Empty string (optional field)
    ]

    with app.app_context():
        schema = CustomerSchema(session=db.session)

        for phone in valid_phones:
            data = {
                "name": "Test Customer",
                "phone_number": phone,
            }
            # Should not raise ValidationError
            result = schema.load(data)
            # Empty string stays as empty string, not converted to None
            assert result.phone_number == phone


def test_customer_phone_number_invalid_formats(app):
    """Test that invalid phone numbers are rejected."""
    invalid_phones = [
        "call me",  # Contains letters
        "phone@example.com",  # Contains @ symbol
        "123#456",  # Contains # symbol
        "tel: 123456",  # Contains colon
        "abcd1234",  # Contains letters
    ]

    with app.app_context():
        schema = CustomerSchema(session=db.session)

        for phone in invalid_phones:
            data = {
                "name": "Test Customer",
                "phone_number": phone,
            }
            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)
            assert "phone_number" in exc_info.value.messages


def test_subcontractor_phone_number_valid_formats(app):
    """Test that subcontractor phone validation accepts international formats."""
    valid_phones = [
        "+33 1 23 45 67 89",  # International with spaces
        "(555) 123-4567",  # US format
        "0123456789",  # Digits only
        "+1-555-123-4567",  # International with dashes
        "",  # Empty string (optional field)
    ]

    with app.app_context():
        schema = SubcontractorSchema(session=db.session)

        for phone in valid_phones:
            data = {
                "name": f"Test Subcontractor {phone[:5]}",  # Unique name
                "phone_number": phone,
            }
            # Should not raise ValidationError
            result = schema.load(data)
            # Empty string stays as empty string, not converted to None
            assert result.phone_number == phone


def test_subcontractor_phone_number_invalid_formats(app):
    """Test that invalid phone numbers are rejected for subcontractors."""
    invalid_phones = [
        "call me",  # Contains letters
        "email@test.com",  # Email format
        "123#456",  # Contains invalid character
    ]

    with app.app_context():
        schema = SubcontractorSchema(session=db.session)

        for phone in invalid_phones:
            data = {
                "name": f"Test Sub {phone[:5]}",  # Unique name
                "phone_number": phone,
            }
            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)
            assert "phone_number" in exc_info.value.messages


def test_customer_phone_number_length_validation(app):
    """Test that phone numbers exceeding max length are rejected."""
    with app.app_context():
        schema = CustomerSchema(session=db.session)

        # 51 characters (exceeds max of 50)
        long_phone = "+" + "1" * 50

        data = {
            "name": "Test Customer",
            "phone_number": long_phone,
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert "phone_number" in exc_info.value.messages


def test_phone_number_none_allowed(app):
    """Test that None is allowed for phone_number (optional field)."""
    with app.app_context():
        customer_schema = CustomerSchema(session=db.session)
        subcontractor_schema = SubcontractorSchema(session=db.session)

        # Customer with None phone_number
        customer_data = {
            "name": "Test Customer",
            "phone_number": None,
        }
        customer = customer_schema.load(customer_data)
        assert customer.phone_number is None

        # Subcontractor with None phone_number
        subcontractor_data = {
            "name": "Test Subcontractor",
            "phone_number": None,
        }
        subcontractor = subcontractor_schema.load(subcontractor_data)
        assert subcontractor.phone_number is None
