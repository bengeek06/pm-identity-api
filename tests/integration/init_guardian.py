#!/usr/bin/env python3

# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
init_guardian.py
================

Initialize Guardian Service for integration tests.

This script:
1. Calls /init-db to create default permissions
2. Creates an "Integration Admin" role
3. Creates a policy with all permissions
4. Associates the policy with the admin role
5. Returns the admin role_id to be used in tests

The company_id and user_id will be created by fixtures in conftest.py
"""

import sys

import requests

GUARDIAN_URL = "http://localhost:5002"
TIMEOUT = 5


def init_guardian_db():
    """Initialize Guardian database with default permissions."""
    try:
        response = requests.post(f"{GUARDIAN_URL}/init-db", timeout=TIMEOUT)
        if response.status_code in [
            200,
            409,
        ]:  # 200=initialized, 409=already done
            print(
                f"✓ Guardian /init-db: {response.json().get('message', 'OK')}"
            )
            return True
        print(
            f"✗ Guardian /init-db failed: {response.status_code} - {response.text}"
        )
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Guardian /init-db error: {e}")
        return False


def get_all_permissions():
    """Get all available permissions from Guardian."""
    try:
        response = requests.get(f"{GUARDIAN_URL}/permissions", timeout=TIMEOUT)
        if response.status_code == 200:
            permissions = response.json()
            print(f"✓ Found {len(permissions)} permissions")
            return permissions
        print(f"✗ Failed to get permissions: {response.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"✗ Error getting permissions: {e}")
        return []


def create_admin_role(company_id, token):
    """Create Integration Admin role."""
    try:
        headers = {"Cookie": f"access_token={token}"}
        data = {
            "name": "Integration Admin",
            "description": "Full access role for integration tests",
            "company_id": company_id,
        }
        response = requests.post(
            f"{GUARDIAN_URL}/roles",
            json=data,
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code == 201:
            role = response.json()
            print(f"✓ Created admin role: {role['id']}")
            return role
        print(
            f"✗ Failed to create admin role: {response.status_code} - {response.text}"
        )
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error creating admin role: {e}")
        return None


def create_admin_policy(company_id, token):
    """Create Integration Admin policy."""
    try:
        headers = {"Cookie": f"access_token={token}"}
        data = {
            "name": "Integration Admin Policy",
            "description": "All permissions for integration tests",
            "company_id": company_id,
        }
        response = requests.post(
            f"{GUARDIAN_URL}/policies",
            json=data,
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code == 201:
            policy = response.json()
            print(f"✓ Created admin policy: {policy['id']}")
            return policy
        print(
            "✗ Failed to create admin policy: "
            f"{response.status_code} - {response.text}"
        )
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error creating admin policy: {e}")
        return None


def associate_permissions_to_policy(policy_id, permissions, token):
    """Associate all permissions to the admin policy."""
    headers = {"Cookie": f"access_token={token}"}
    success_count = 0

    for perm in permissions:
        try:
            data = {"permission_id": perm["id"]}
            response = requests.post(
                f"{GUARDIAN_URL}/policies/{policy_id}/permissions/{perm['id']}",
                json=data,
                headers=headers,
                timeout=TIMEOUT,
            )
            if response.status_code in [
                201,
                409,
            ]:  # 201=created, 409=already exists
                success_count += 1
        except requests.exceptions.RequestException:
            pass

    print(
        f"✓ Associated {success_count}/{len(permissions)} permissions to policy"
    )
    return success_count > 0


def associate_policy_to_role(role_id, policy_id, token):
    """Associate admin policy to admin role."""
    try:
        headers = {"Cookie": f"access_token={token}"}
        data = {"policy_id": policy_id}
        response = requests.post(
            f"{GUARDIAN_URL}/roles/{role_id}/policies/{policy_id}",
            json=data,
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code in [201, 409]:
            print("✓ Associated policy to role")
            return True
        print(f"✗ Failed to associate policy: {response.status_code}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Error associating policy: {e}")
        return False


def main(company_id, token):
    """
    Main initialization function.

    Args:
        company_id: Company ID for multi-tenant isolation
        token: JWT token for authentication

    Returns:
        role_id on success, None on failure
    """
    print("\n🔧 Initializing Guardian Service...")
    print(f"   Company ID: {company_id}")

    # Step 1: Initialize database with default permissions
    if not init_guardian_db():
        return None

    # Step 2: Get all permissions
    permissions = get_all_permissions()
    if not permissions:
        return None

    # Step 3: Create admin role
    role = create_admin_role(company_id, token)
    if not role:
        return None

    # Step 4: Create admin policy
    policy = create_admin_policy(company_id, token)
    if not policy:
        return None

    # Step 5: Associate all permissions to policy
    if not associate_permissions_to_policy(policy["id"], permissions, token):
        return None

    # Step 6: Associate policy to role
    if not associate_policy_to_role(role["id"], policy["id"], token):
        return None

    print("✅ Guardian initialized successfully!")
    print(f"   Admin Role ID: {role['id']}")

    # Return role_id for use in tests
    return role["id"]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: init_guardian.py <company_id> <jwt_token>")
        sys.exit(1)

    company_id = sys.argv[1]
    token = sys.argv[2]

    role_id = main(company_id, token)
    if role_id:
        # Print role_id to stdout for capture
        print(f"ADMIN_ROLE_ID={role_id}")
        sys.exit(0)
    else:
        sys.exit(1)
