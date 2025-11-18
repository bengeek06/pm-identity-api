"""
Tests for utility functions in app.utils module.
"""

import pytest
from unittest import mock

import requests
from flask import Flask

from app.utils import check_access


class TestCheckAccess:
    """Test cases for check_access function."""

    @pytest.mark.skip(reason="Need refactor")
    def test_check_access_guardian_disabled(self, app):
        """Test that check_access returns True when Guardian Service is disabled."""
        with app.app_context():
            app.config["USE_GUARDIAN_SERVICE"] = False
            access_granted, reason, status = check_access(
                "user123", "user", "list"
            )
            assert access_granted is True
            assert (
                "guardian service is disabled" in reason.lower()
                or "bypassing" in reason.lower()
            )
            assert status == 200

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
