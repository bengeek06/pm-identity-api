# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
Tests for utility functions in app.utils module.
"""

from unittest import mock

import pytest
import requests

from app.utils import check_access, check_access_required


class TestCheckAccess:
    """Test cases for check_access function."""

    def test_check_access_guardian_enabled_success(self, app):
        """Test successful access check with Guardian service enabled and returning 200."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_granted": True,
                "reason": "User has permission",
                "status": 200,
            }

            with mock.patch(
                "requests.post", return_value=mock_response
            ) as mock_post:
                access_granted, reason, status = check_access(
                    "user123", "user", "list"
                )

                assert access_granted is True
                assert reason == "User has permission"
                assert status == 200

                # Verify the correct API call was made
                mock_post.assert_called_once_with(
                    "http://guardian:8000/check-access",
                    json={
                        "user_id": "user123",
                        "service": "identity",
                        "resource_name": "user",
                        "operation": "list",
                    },
                    headers={},
                    timeout=5.0,
                )

    def test_check_access_guardian_denied_200(self, app):
        """Test access denied with Guardian service returning 200."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_granted": False,
                "reason": "Insufficient permissions",
                "status": 403,
            }

            with mock.patch("requests.post", return_value=mock_response):
                access_granted, reason, status = check_access(
                    "user123", "user", "list"
                )

                assert access_granted is False
                assert reason == "Insufficient permissions"
                assert status == 403

    def test_check_access_guardian_400_with_json(self, app):
        """Test Guardian service returning 400 with JSON error message."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "access_granted": False,
                "reason": "Invalid user_id format",
            }

            with mock.patch("requests.post", return_value=mock_response):
                access_granted, reason, status = check_access(
                    "invalid-user", "user", "list"
                )

                assert access_granted is False
                assert reason == "Invalid user_id format"
                assert status == 400

    def test_check_access_guardian_400_without_json(self, app):
        """Test Guardian service returning 400 without JSON response."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 400
            mock_response.json.side_effect = ValueError(
                "No JSON object could be decoded"
            )
            mock_response.text = "Bad Request: Invalid parameters"

            with mock.patch("requests.post", return_value=mock_response):
                access_granted, reason, status = check_access(
                    "user123", "user", "list"
                )

                assert access_granted is False
                assert (
                    "Guardian service error: Bad Request: Invalid parameters"
                    in reason
                )
                assert status == 400

    def test_check_access_guardian_500(self, app):
        """Test Guardian service returning 500."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            with mock.patch("requests.post", return_value=mock_response):
                access_granted, reason, status = check_access(
                    "user123", "user", "list"
                )

                assert access_granted is False
                assert "Guardian service error (status 500)" in reason
                assert status == 500

    def test_check_access_guardian_timeout(self, app):
        """Test Guardian service timeout."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            with mock.patch(
                "requests.post", side_effect=requests.exceptions.Timeout
            ):
                access_granted, reason, status = check_access(
                    "user123", "user", "list"
                )

                assert access_granted is False
                assert "timeout" in reason.lower()
                assert status == 504

    def test_check_access_guardian_connection_error(self, app):
        """Test Guardian service connection error."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            with mock.patch(
                "requests.post",
                side_effect=requests.exceptions.ConnectionError,
            ):
                access_granted, reason, status = check_access(
                    "user123", "user", "list"
                )

                assert access_granted is False
                assert "internal server error" in reason.lower()
                assert status == 500

    def test_check_access_custom_timeout(self, app):
        """Test that custom timeout is used when set."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 10.0

            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_granted": True,
                "reason": "Success",
                "status": 200,
            }

            with mock.patch(
                "requests.post", return_value=mock_response
            ) as mock_post:
                check_access("user123", "user", "list")

                # Verify custom timeout was used
                mock_post.assert_called_once_with(
                    "http://guardian:8000/check-access",
                    json={
                        "user_id": "user123",
                        "service": "identity",
                        "resource_name": "user",
                        "operation": "list",
                    },
                    headers={},
                    timeout=10.0,
                )

    def test_check_access_forwards_jwt_cookie(self, app):
        """Test that check_access forwards JWT cookie to Guardian service."""
        with app.test_request_context(
            "/", headers={"Cookie": "access_token=test-jwt-token"}
        ):
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_granted": True,
                "reason": "Success",
                "status": 200,
            }

            with mock.patch(
                "requests.post", return_value=mock_response
            ) as mock_post:
                check_access("user123", "user", "list")

                # Verify the JWT cookie was forwarded in headers
                mock_post.assert_called_once_with(
                    "http://guardian:8000/check-access",
                    json={
                        "user_id": "user123",
                        "service": "identity",
                        "resource_name": "user",
                        "operation": "list",
                    },
                    headers={"Cookie": "access_token=test-jwt-token"},
                    timeout=5.0,
                )

    def test_check_access_without_jwt_cookie(self, app):
        """Test that check_access works without JWT cookie (no headers added)."""
        with app.test_request_context("/"):
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_granted": True,
                "reason": "Success",
                "status": 200,
            }

            with mock.patch(
                "requests.post", return_value=mock_response
            ) as mock_post:
                check_access("user123", "user", "list")

                # Verify no Cookie header was added when no cookie present
                mock_post.assert_called_once_with(
                    "http://guardian:8000/check-access",
                    json={
                        "user_id": "user123",
                        "service": "identity",
                        "resource_name": "user",
                        "operation": "list",
                    },
                    headers={},
                    timeout=5.0,
                )

    def test_check_access_operations_sent_uppercase(self, app):
        """Test that operations are sent to Guardian in uppercase format."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = True
            app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8000"
            app.config["GUARDIAN_SERVICE_TIMEOUT"] = 5

            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_granted": True,
                "reason": "Access granted",
                "status": 200,
            }

            operations = ["LIST", "CREATE", "READ", "UPDATE", "DELETE"]

            with mock.patch(
                "requests.post", return_value=mock_response
            ) as mock_post:
                for operation in operations:
                    mock_post.reset_mock()

                    # Call check_access with uppercase operation
                    check_access("user123", "company", operation)

                    # Verify the operation is sent in uppercase
                    call_args = mock_post.call_args
                    assert (
                        call_args[1]["json"]["operation"] == operation
                    ), f"Operation {operation} should be sent as uppercase"


class TestCheckAccessRequiredDecorator:
    """Test cases for check_access_required decorator."""

    def test_decorator_validates_operation_uppercase_only(self):
        """Test that the decorator only accepts uppercase operations."""
        # pylint: disable=import-outside-toplevel
        from flask_restful import Resource

        def create_valid_resource(operation):
            """Factory to create resource with given operation."""

            class ValidResource(Resource):
                """Test resource with valid operation."""

                @check_access_required(operation)
                def get(self):
                    """GET method for testing."""
                    return {"message": "ok"}

            return ValidResource

        def create_invalid_resource(operation):
            """Factory to create resource with given operation."""

            class InvalidResource(Resource):
                """Test resource with invalid operation."""

                @check_access_required(operation)
                def get(self):
                    """GET method for testing."""
                    return {"message": "ok"}

            return InvalidResource

        # Valid operations (uppercase) should not raise
        valid_operations = ["LIST", "CREATE", "READ", "UPDATE", "DELETE"]
        for op in valid_operations:
            try:
                create_valid_resource(op)
            except ValueError:
                pytest.fail(f"Valid operation '{op}' raised ValueError")

        # Invalid operations (lowercase or wrong) should raise ValueError
        invalid_operations = ["list", "create", "invalid", "list_all"]
        for op in invalid_operations:
            with pytest.raises(ValueError, match="Invalid operation"):
                create_invalid_resource(op)
