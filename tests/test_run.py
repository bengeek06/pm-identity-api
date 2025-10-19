"""
Test suite for the run module of a Flask application.

This module tests the configuration mapping logic based on the
environment variable `FLASK_ENV` and the main application startup.
"""

import os
from unittest.mock import patch, MagicMock

import pytest
from run import main


@pytest.mark.parametrize(
    "env,expected_config",
    [
        ("production", "app.config.ProductionConfig"),
        ("staging", "app.config.StagingConfig"),
        ("testing", "app.config.TestingConfig"),
        ("development", "app.config.DevelopmentConfig"),
        ("unknown", "app.config.DevelopmentConfig"),
    ],
)
def test_run_config_mapping(env, expected_config):
    """
    Test that the run module correctly maps FLASK_ENV to the right configuration class.
    """
    # Set environment
    original_env = os.environ.get("FLASK_ENV")
    original_port = os.environ.get("PORT")

    os.environ["FLASK_ENV"] = env
    os.environ["PORT"] = "5000"  # Set default port

    try:
        # Mock all external dependencies
        mock_create_app = MagicMock()
        mock_logger = MagicMock()

        # Mock the app instance to prevent actual server startup
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        with (
            patch("run.create_app", mock_create_app),
            patch("run.logger", mock_logger),
        ):
            # Call main function
            main()

            # Verify create_app was called with correct config
            mock_create_app.assert_called_once_with(expected_config)

            # Verify app.run was called with correct parameters
            expected_debug = env in ["development", "testing"]
            mock_app.run.assert_called_once_with(
                host="0.0.0.0", port=5000, debug=expected_debug
            )

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["FLASK_ENV"] = original_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]

        if original_port is not None:
            os.environ["PORT"] = original_port
        elif "PORT" in os.environ:
            del os.environ["PORT"]


def test_main_with_custom_port():
    """
    Test that the main function uses custom PORT environment variable.
    """
    original_env = os.environ.get("FLASK_ENV")
    original_port = os.environ.get("PORT")

    os.environ["FLASK_ENV"] = "development"
    os.environ["PORT"] = "8080"

    try:
        mock_create_app = MagicMock()
        mock_logger = MagicMock()
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        with (
            patch("run.create_app", mock_create_app),
            patch("run.logger", mock_logger),
        ):
            main()

            # Verify app.run was called with custom port
            mock_app.run.assert_called_once_with(
                host="0.0.0.0", port=8080, debug=True
            )

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["FLASK_ENV"] = original_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]

        if original_port is not None:
            os.environ["PORT"] = original_port
        elif "PORT" in os.environ:
            del os.environ["PORT"]


def test_main_debug_mode_logic():
    """
    Test that debug mode is correctly set based on environment.
    """
    test_cases = [
        ("production", False),
        ("staging", False),
        ("development", True),
        ("testing", True),
    ]

    for env, expected_debug in test_cases:
        original_env = os.environ.get("FLASK_ENV")
        os.environ["FLASK_ENV"] = env

        try:
            mock_create_app = MagicMock()
            mock_logger = MagicMock()
            mock_app = MagicMock()
            mock_create_app.return_value = mock_app

            with (
                patch("run.create_app", mock_create_app),
                patch("run.logger", mock_logger),
            ):
                main()

                # Verify debug mode is set correctly
                mock_app.run.assert_called_once_with(
                    host="0.0.0.0", port=5000, debug=expected_debug
                )

        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["FLASK_ENV"] = original_env
            elif "FLASK_ENV" in os.environ:
                del os.environ["FLASK_ENV"]
