"""
Test suite for the run module of a Flask application.

This module tests the configuration mapping logic based on the
environment variable `FLASK_ENV`.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


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
def test_run_config_mapping(monkeypatch, env, expected_config):
    """
    Test that the run module correctly maps FLASK_ENV to the right configuration class.
    """
    # Set environment
    original_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = env

    try:
        # Import run module to access its config mapping logic
        from run import main

        # Mock all external dependencies
        mock_load_dotenv = MagicMock()
        mock_create_app = MagicMock()
        mock_logger = MagicMock()

        # Mock the app instance to prevent actual server startup
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        with patch("run.load_dotenv", mock_load_dotenv), patch(
            "run.create_app", mock_create_app
        ), patch("run.logger", mock_logger), patch(
            "run.os.path.exists", return_value=False
        ):  # No .env file

            # Call main function
            main()

            # Verify create_app was called with correct config
            mock_create_app.assert_called_once_with(expected_config)

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["FLASK_ENV"] = original_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]
