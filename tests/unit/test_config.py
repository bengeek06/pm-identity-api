# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
test_config.py
--------------
This module contains tests for the /config endpoint to ensure it returns the
expected configuration values.
"""

import json
import uuid

from tests.unit.conftest import create_jwt_token


def test_config_endpoit(client):
    """
    Test the /config endpoint to ensure it returns the correct configuration.
    """
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    token = create_jwt_token(company_id, user_id)
    client.set_cookie("access_token", token, domain="localhost")

    response = client.get("/config")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert isinstance(data, dict)

    # Core environment variables
    assert "FLASK_ENV" in data
    assert "LOG_LEVEL" in data
    assert "DATABASE_URL" in data

    # Guardian Service configuration
    assert "USE_GUARDIAN_SERVICE" in data
    assert "GUARDIAN_SERVICE_URL" in data
    assert "GUARDIAN_SERVICE_TIMEOUT" in data

    # Storage Service configuration
    assert "USE_STORAGE_SERVICE" in data
    assert "STORAGE_SERVICE_URL" in data
    assert "STORAGE_REQUEST_TIMEOUT" in data
    assert "MAX_AVATAR_SIZE_MB" in data

    # Security tokens (should only show if set, not the actual values)
    assert "JWT_SECRET_SET" in data
    assert "INTERNAL_AUTH_TOKEN_SET" in data
    assert isinstance(data["JWT_SECRET_SET"], bool)
    assert isinstance(data["INTERNAL_AUTH_TOKEN_SET"], bool)
