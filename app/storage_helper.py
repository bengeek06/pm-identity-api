# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
storage_helper.py
=================

Helper functions for interacting with the Storage Service.
Provides avatar upload/delete functionality for the Identity Service.
"""

import requests

from app.logger import logger


def is_storage_service_enabled() -> bool:
    """Check if Storage Service integration is enabled."""
    from flask import current_app  # pylint: disable=import-outside-toplevel

    return current_app.config.get("USE_STORAGE_SERVICE", False)


# Allowed MIME types for avatars
ALLOWED_AVATAR_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}


class StorageServiceError(Exception):
    """Exception raised when Storage Service operations fail."""


class AvatarValidationError(Exception):
    """Exception raised when avatar validation fails."""


def validate_avatar(
    file_data: bytes, content_type: str, max_size: int = None
) -> None:
    """
    Validate an avatar file.

    Args:
        file_data: Binary file data
        content_type: MIME type of the file
        max_size: Maximum size in bytes (default from config)

    Raises:
        AvatarValidationError: If validation fails
    """
    from flask import current_app  # pylint: disable=import-outside-toplevel

    if max_size is None:
        max_size = (
            current_app.config.get("MAX_AVATAR_SIZE_MB", 5) * 1024 * 1024
        )

    if not file_data:
        logger.error("Avatar file is empty")
        raise AvatarValidationError("Avatar file is empty")

    if len(file_data) > max_size:
        size_mb = len(file_data) / 1024 / 1024
        max_mb = max_size / 1024 / 1024
        logger.error(f"Avatar too large: {size_mb:.2f} MB (max: {max_mb} MB)")
        raise AvatarValidationError(
            f"Avatar too large: {size_mb:.2f} MB (max: {max_mb} MB)"
        )

    if content_type not in ALLOWED_AVATAR_TYPES:
        logger.error(
            f"Invalid content type: {content_type}. Allowed: {', '.join(ALLOWED_AVATAR_TYPES)}"
        )
        raise AvatarValidationError(
            f"Invalid content type: {content_type}. "
            f"Allowed: {', '.join(ALLOWED_AVATAR_TYPES)}"
        )


def _prepare_avatar_upload_request(
    user_id: str,
    company_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
):
    """Prepare upload request data for avatar."""
    # Normalisation: toujours utiliser .png comme extension
    # Le vrai type (JPEG, PNG, etc.) est préservé dans content_type
    # et sera retourné par le Storage Service au download via le header Content-Type HTTP
    # Le navigateur lit le Content-Type HTTP, pas l'extension de l'URL
    extension = "png"
    logical_path = f"avatars/{user_id}.{extension}"
    logger.debug(f"Logical path for avatar: {logical_path}")

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
    }

    files = {
        "file": (filename, file_data, content_type),
    }

    data = {
        "bucket_type": "users",
        "bucket_id": user_id,
        "logical_path": logical_path,
    }

    return headers, files, data


def _prepare_logo_upload_request(
    company_id: str,
    user_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
):
    """Prepare upload request data for company logo."""
    # Normalisation: toujours utiliser .png comme extension
    # Le vrai type (JPEG, PNG, etc.) est préservé dans content_type
    # et sera retourné par le Storage Service au download via le header Content-Type HTTP
    # Le navigateur lit le Content-Type HTTP, pas l'extension de l'URL
    extension = "png"
    logical_path = f"logos/{company_id}.{extension}"
    logger.debug(f"Logical path for logo: {logical_path}")

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
    }

    files = {
        "file": (filename, file_data, content_type),
    }

    data = {
        "bucket_type": "companies",
        "bucket_id": company_id,
        "logical_path": logical_path,
    }

    return headers, files, data


def _prepare_customer_logo_upload_request(
    customer_id: str,
    company_id: str,
    user_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
):
    """Prepare upload request data for customer logo."""
    extension = "png"
    logical_path = f"customers/{customer_id}/logo.{extension}"
    logger.debug(f"Logical path for customer logo: {logical_path}")

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
    }

    files = {
        "file": (filename, file_data, content_type),
    }

    data = {
        "bucket_type": "companies",
        "bucket_id": company_id,
        "logical_path": logical_path,
    }

    return headers, files, data


def _prepare_subcontractor_logo_upload_request(
    subcontractor_id: str,
    company_id: str,
    user_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
):
    """Prepare upload request data for subcontractor logo."""
    extension = "png"
    logical_path = f"subcontractors/{subcontractor_id}/logo.{extension}"
    logger.debug(f"Logical path for subcontractor logo: {logical_path}")

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
    }

    files = {
        "file": (filename, file_data, content_type),
    }

    data = {
        "bucket_type": "companies",
        "bucket_id": company_id,
        "logical_path": logical_path,
    }

    return headers, files, data


def _extract_object_key_from_response(result):
    """Extract object_key from Storage Service response."""
    object_key = result.get("object_key")
    if not object_key and "data" in result:
        object_key = result["data"].get("object_key")

    if not object_key:
        raise StorageServiceError(
            f"Storage Service did not return object_key. Response: {result}"
        )

    return object_key


def upload_avatar_via_proxy(  # pylint: disable=too-many-locals
    user_id: str,
    company_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
) -> dict:
    """
    Upload an avatar via the Storage Service proxy endpoint.

    This is the simplified approach that uploads the file in a single request.

    Args:
        user_id: UUID of the user
        company_id: UUID of the company
        file_data: Binary file data
        content_type: MIME type (e.g., "image/jpeg")
        filename: Original filename

    Returns:
        dict: {
            'file_id': 'uuid-from-storage',
            'object_key': 'users/...'  # for legacy/debugging
        }
        If Storage Service is disabled, returns mock data.

    Raises:
        AvatarValidationError: If validation fails
        StorageServiceError: If upload fails
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping avatar upload for user {user_id}"
        )
        # Return mock file_id for autonomous mode
        return {
            "file_id": f"mock-file-id-{user_id}",
            "object_key": "mock-object-key",
        }

    # Validate the file
    validate_avatar(file_data, content_type)

    # Prepare request components
    headers, files, data = _prepare_avatar_upload_request(
        user_id, company_id, file_data, content_type, filename
    )

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/upload/proxy"
    logger.debug(f"Uploading avatar for user {user_id} to {url}")

    try:
        logger.info(
            f"Uploading avatar for user {user_id}: {len(file_data)} bytes"
        )

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.post(
            url,
            files=files,
            data=data,
            headers=headers,
            timeout=timeout,
        )

        logger.debug(
            f"Storage Service response status: {response.status_code}"
        )

        # Accept both 200 and 201 as success
        if response.status_code not in (200, 201):
            logger.error(
                f"Failed to upload avatar: {response.status_code} {response.text}"
            )
            response.raise_for_status()

        result = response.json()
        logger.debug(f"Storage Service response: {result}")

        # Extract file_id from response
        file_id = result.get("file_id")
        if not file_id and "data" in result:
            file_id = result["data"].get("file_id")

        if not file_id:
            logger.error(
                f"Storage Service did not return file_id. Response: {result}"
            )
            raise StorageServiceError("Storage Service did not return file_id")

        # Extract object_key from response
        object_key = _extract_object_key_from_response(result)

        logger.info(f"Avatar uploaded successfully: file_id={file_id}")
        logger.debug(f"object_key: {object_key}")
        return {"file_id": file_id, "object_key": object_key}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        raise StorageServiceError("Storage Service timeout") from None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Storage Service: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except ValueError:
                error_msg = str(e)
        else:
            error_msg = str(e)
        raise StorageServiceError(f"Storage Service error: {error_msg}") from e


def upload_logo_via_proxy(  # pylint: disable=too-many-locals
    company_id: str,
    user_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
) -> dict:
    """
    Upload a company logo via the Storage Service proxy endpoint.

    Args:
        company_id: UUID of the company
        user_id: UUID of the user (for auth)
        file_data: Binary file data
        content_type: MIME type (e.g., "image/jpeg")
        filename: Original filename

    Returns:
        dict: {
            'file_id': 'uuid-from-storage',
            'object_key': 'companies/...'
        }
        If Storage Service is disabled, returns mock data.

    Raises:
        AvatarValidationError: If validation fails
        StorageServiceError: If upload fails
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping logo upload for company {company_id}"
        )
        # Return mock file_id for autonomous mode
        return {
            "file_id": f"mock-file-id-{company_id}",
            "object_key": "mock-object-key",
        }

    # Validate the file (use same validation as avatars)
    validate_avatar(file_data, content_type)

    # Prepare request components
    headers, files, data = _prepare_logo_upload_request(
        company_id, user_id, file_data, content_type, filename
    )

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/upload/proxy"
    logger.debug(f"Uploading logo for company {company_id} to {url}")

    try:
        logger.info(
            f"Uploading logo for company {company_id}: {len(file_data)} bytes"
        )

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.post(
            url,
            files=files,
            data=data,
            headers=headers,
            timeout=timeout,
        )

        logger.debug(
            f"Storage Service response status: {response.status_code}"
        )

        # Accept both 200 and 201 as success
        if response.status_code not in (200, 201):
            logger.error(
                f"Failed to upload logo: {response.status_code} {response.text}"
            )
            response.raise_for_status()

        result = response.json()
        logger.debug(f"Storage Service response: {result}")

        # Extract file_id from response
        file_id = result.get("file_id")
        if not file_id and "data" in result:
            file_id = result["data"].get("file_id")

        if not file_id:
            logger.error(
                f"Storage Service did not return file_id. Response: {result}"
            )
            raise StorageServiceError("Storage Service did not return file_id")

        # Extract object_key from response
        object_key = _extract_object_key_from_response(result)

        logger.info(f"Logo uploaded successfully: file_id={file_id}")
        logger.debug(f"object_key: {object_key}")
        return {"file_id": file_id, "object_key": object_key}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        raise StorageServiceError("Storage Service timeout") from None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Storage Service: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except ValueError:
                error_msg = str(e)
        else:
            error_msg = str(e)
        raise StorageServiceError(f"Storage Service error: {error_msg}") from e


def upload_customer_logo_via_proxy(  # pylint: disable=too-many-locals
    customer_id: str,
    company_id: str,
    user_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
) -> dict:
    """
    Upload a customer logo via the Storage Service proxy endpoint.

    Args:
        customer_id: UUID of the customer
        company_id: UUID of the company
        user_id: UUID of the user (for auth)
        file_data: Binary file data
        content_type: MIME type (e.g., "image/jpeg")
        filename: Original filename

    Returns:
        dict: {
            'file_id': 'uuid-from-storage',
            'object_key': 'companies/.../customers/...'
        }
        If Storage Service is disabled, returns mock data.

    Raises:
        AvatarValidationError: If validation fails
        StorageServiceError: If upload fails
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping logo upload for customer {customer_id}"
        )
        return {
            "file_id": f"mock-file-id-{customer_id}",
            "object_key": "mock-object-key",
        }

    validate_avatar(file_data, content_type)

    headers, files, data = _prepare_customer_logo_upload_request(
        customer_id, company_id, user_id, file_data, content_type, filename
    )

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/upload/proxy"
    logger.debug(f"Uploading logo for customer {customer_id} to {url}")

    try:
        logger.info(
            f"Uploading logo for customer {customer_id}: {len(file_data)} bytes"
        )

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.post(
            url,
            files=files,
            data=data,
            headers=headers,
            timeout=timeout,
        )

        logger.debug(
            f"Storage Service response status: {response.status_code}"
        )

        if response.status_code not in (200, 201):
            logger.error(
                f"Failed to upload customer logo: {response.status_code} {response.text}"
            )
            response.raise_for_status()

        result = response.json()
        logger.debug(f"Storage Service response: {result}")

        file_id = result.get("file_id")
        if not file_id and "data" in result:
            file_id = result["data"].get("file_id")

        if not file_id:
            logger.error(
                f"Storage Service did not return file_id. Response: {result}"
            )
            raise StorageServiceError("Storage Service did not return file_id")

        object_key = _extract_object_key_from_response(result)

        logger.info(f"Customer logo uploaded successfully: file_id={file_id}")
        logger.debug(f"object_key: {object_key}")
        return {"file_id": file_id, "object_key": object_key}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        raise StorageServiceError("Storage Service timeout") from None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Storage Service: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except ValueError:
                error_msg = str(e)
        else:
            error_msg = str(e)
        raise StorageServiceError(f"Storage Service error: {error_msg}") from e


def upload_subcontractor_logo_via_proxy(  # pylint: disable=too-many-locals
    subcontractor_id: str,
    company_id: str,
    user_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
) -> dict:
    """
    Upload a subcontractor logo via the Storage Service proxy endpoint.

    Args:
        subcontractor_id: UUID of the subcontractor
        company_id: UUID of the company
        user_id: UUID of the user (for auth)
        file_data: Binary file data
        content_type: MIME type (e.g., "image/jpeg")
        filename: Original filename

    Returns:
        dict: {
            'file_id': 'uuid-from-storage',
            'object_key': 'companies/.../subcontractors/...'
        }
        If Storage Service is disabled, returns mock data.

    Raises:
        AvatarValidationError: If validation fails
        StorageServiceError: If upload fails
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping logo upload for subcontractor {subcontractor_id}"
        )
        return {
            "file_id": f"mock-file-id-{subcontractor_id}",
            "object_key": "mock-object-key",
        }

    validate_avatar(file_data, content_type)

    headers, files, data = _prepare_subcontractor_logo_upload_request(
        subcontractor_id, company_id, user_id, file_data, content_type, filename
    )

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/upload/proxy"
    logger.debug(f"Uploading logo for subcontractor {subcontractor_id} to {url}")

    try:
        logger.info(
            f"Uploading logo for subcontractor {subcontractor_id}: {len(file_data)} bytes"
        )

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.post(
            url,
            files=files,
            data=data,
            headers=headers,
            timeout=timeout,
        )

        logger.debug(
            f"Storage Service response status: {response.status_code}"
        )

        if response.status_code not in (200, 201):
            logger.error(
                f"Failed to upload subcontractor logo: {response.status_code} {response.text}"
            )
            response.raise_for_status()

        result = response.json()
        logger.debug(f"Storage Service response: {result}")

        file_id = result.get("file_id")
        if not file_id and "data" in result:
            file_id = result["data"].get("file_id")

        if not file_id:
            logger.error(
                f"Storage Service did not return file_id. Response: {result}"
            )
            raise StorageServiceError("Storage Service did not return file_id")

        object_key = _extract_object_key_from_response(result)

        logger.info(f"Subcontractor logo uploaded successfully: file_id={file_id}")
        logger.debug(f"object_key: {object_key}")
        return {"file_id": file_id, "object_key": object_key}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        raise StorageServiceError("Storage Service timeout") from None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Storage Service: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except ValueError:
                error_msg = str(e)
        else:
            error_msg = str(e)
        raise StorageServiceError(f"Storage Service error: {error_msg}") from e


def delete_avatar(user_id: str, company_id: str, file_id: str) -> None:
    """
    Delete a user's avatar from the Storage Service.

    Args:
        user_id (str): The user's ID
        company_id (str): The user's company ID
        file_id (str): The file ID of the avatar to delete (from file_id field)

    Note:
        This function does not raise exceptions if deletion fails,
        as deletion is not critical to the update operation.
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping avatar deletion for user {user_id}"
        )
        return

    if not file_id:
        logger.warning("No file_id provided for deletion")
        return

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/delete"

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
        "Content-Type": "application/json",
    }

    # The Storage Service DELETE endpoint expects file_id
    payload = {
        "file_id": file_id,
        "physical": True,  # Permanent deletion
    }

    try:
        logger.info(f"Deleting avatar with file_id: {file_id}")

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.delete(
            url, json=payload, headers=headers, timeout=timeout
        )

        # Accept both 200 and 404 (already deleted)
        if response.status_code in (200, 204, 404):
            logger.info(f"Avatar deleted successfully: file_id={file_id}")
            return

        # Log the error response for debugging
        logger.error(
            f"Failed to delete avatar: {response.status_code} - {response.text}"
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        # Don't raise - deletion is not critical
        logger.warning("Avatar deletion failed, but continuing")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting avatar: {e}")
        # Don't raise - deletion is not critical
        logger.warning("Avatar deletion failed, but continuing")


def delete_logo(company_id: str, user_id: str, file_id: str) -> None:
    """
    Delete a company's logo from the Storage Service.

    Args:
        company_id (str): The company's ID
        user_id (str): The user's ID (for auth)
        file_id (str): The file ID of the logo to delete (from file_id field)

    Note:
        This function does not raise exceptions if deletion fails,
        as deletion is not critical to the update operation.
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping logo deletion for company {company_id}"
        )
        return

    if not file_id:
        logger.warning("No file_id provided for deletion")
        return

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/delete"

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
        "Content-Type": "application/json",
    }

    # The Storage Service DELETE endpoint expects file_id
    payload = {
        "file_id": file_id,
        "physical": True,  # Permanent deletion
    }

    try:
        logger.info(f"Deleting logo with file_id: {file_id}")

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.delete(
            url, json=payload, headers=headers, timeout=timeout
        )

        # Accept both 200 and 404 (already deleted)
        if response.status_code in (200, 204, 404):
            logger.info(f"Logo deleted successfully: file_id={file_id}")
            return

        # Log the error response for debugging
        logger.error(
            f"Failed to delete logo: {response.status_code} - {response.text}"
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        # Don't raise - deletion is not critical
        logger.warning("Logo deletion failed, but continuing")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting logo: {e}")
        # Don't raise - deletion is not critical
        logger.warning("Logo deletion failed, but continuing")


def delete_customer_logo(
    customer_id: str, company_id: str, user_id: str, file_id: str
) -> None:
    """
    Delete a customer's logo from the Storage Service.

    Args:
        customer_id (str): The customer's ID
        company_id (str): The company's ID
        user_id (str): The user's ID (for auth)
        file_id (str): The file ID of the logo to delete

    Note:
        This function does not raise exceptions if deletion fails,
        as deletion is not critical to the update operation.
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping logo deletion for customer {customer_id}"
        )
        return

    if not file_id:
        logger.warning("No file_id provided for deletion")
        return

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/delete"

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
        "Content-Type": "application/json",
    }

    payload = {
        "file_id": file_id,
        "physical": True,
    }

    try:
        logger.info(f"Deleting customer logo with file_id: {file_id}")

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.delete(
            url, json=payload, headers=headers, timeout=timeout
        )

        if response.status_code in (200, 204, 404):
            logger.info(
                f"Customer logo deleted successfully: file_id={file_id}"
            )
            return

        logger.error(
            f"Failed to delete customer logo: {response.status_code} - {response.text}"
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        logger.warning("Customer logo deletion failed, but continuing")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting customer logo: {e}")
        logger.warning("Customer logo deletion failed, but continuing")


def delete_subcontractor_logo(
    subcontractor_id: str, company_id: str, user_id: str, file_id: str
) -> None:
    """
    Delete a subcontractor's logo from the Storage Service.

    Args:
        subcontractor_id (str): The subcontractor's ID
        company_id (str): The company's ID
        user_id (str): The user's ID (for auth)
        file_id (str): The file ID of the logo to delete

    Note:
        This function does not raise exceptions if deletion fails,
        as deletion is not critical to the update operation.
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping logo deletion for subcontractor {subcontractor_id}"
        )
        return

    if not file_id:
        logger.warning("No file_id provided for deletion")
        return

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/delete"

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
        "Content-Type": "application/json",
    }

    payload = {
        "file_id": file_id,
        "physical": True,
    }

    try:
        logger.info(f"Deleting subcontractor logo with file_id: {file_id}")

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.delete(
            url, json=payload, headers=headers, timeout=timeout
        )

        if response.status_code in (200, 204, 404):
            logger.info(
                f"Subcontractor logo deleted successfully: file_id={file_id}"
            )
            return

        logger.error(
            f"Failed to delete subcontractor logo: {response.status_code} - {response.text}"
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Storage Service at {url}")
        logger.warning("Subcontractor logo deletion failed, but continuing")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting subcontractor logo: {e}")
        logger.warning("Subcontractor logo deletion failed, but continuing")


def create_user_directories(user_id: str, company_id: str) -> None:
    """
    Create the user directory structure in the Storage Service.

    Creates:
    - /users/{user_id}/.keep (to ensure user directory exists)
    - /users/{user_id}/workspace/.keep (to ensure workspace directory exists)

    Args:
        user_id: UUID of the user
        company_id: UUID of the company

    Raises:
        StorageServiceError: If directory creation fails
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping directory creation for user {user_id}"
        )
        return

    from flask import current_app  # pylint: disable=import-outside-toplevel

    url = f"{current_app.config['STORAGE_SERVICE_URL']}/upload/proxy"

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
    }

    # Create .keep file content (empty marker file)
    keep_content = b""

    directories = [
        ".keep",  # /users/{user_id}/.keep
        "workspace/.keep",  # /users/{user_id}/workspace/.keep
    ]

    for logical_path in directories:
        files = {
            "file": (".keep", keep_content, "text/plain"),
        }

        data = {
            "bucket_type": "users",
            "bucket_id": user_id,
            "logical_path": logical_path,
        }

        try:
            logger.info(
                f"Creating directory marker: {logical_path} for user {user_id}"
            )

            timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=timeout,
            )

            response.raise_for_status()
            logger.info(f"Directory marker created: {logical_path}")

        except requests.exceptions.Timeout:
            logger.error(f"Timeout creating directory marker: {logical_path}")
            raise StorageServiceError("Storage Service timeout") from None

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error creating directory marker {logical_path}: {e}"
            )
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("message", str(e))
                except ValueError:
                    error_msg = str(e)
            else:
                error_msg = str(e)
            raise StorageServiceError(
                f"Failed to create directory structure: {error_msg}"
            ) from e


def _delete_file_from_storage(
    file_id: str, delete_url: str, headers: dict, timeout: int
) -> None:
    """
    Delete a single file from storage service.

    Args:
        file_id: ID of the file to delete
        delete_url: Storage service delete endpoint URL
        headers: Request headers with user/company IDs
        timeout: Request timeout in seconds
    """
    try:
        delete_payload = {
            "file_id": file_id,
            "physical": True,  # Permanent deletion
        }

        del_response = requests.delete(
            delete_url,
            json=delete_payload,
            headers=headers,
            timeout=timeout,
        )

        if del_response.status_code in (200, 204, 404):
            logger.debug(f"Deleted file {file_id}")
        else:
            logger.warning(
                f"Failed to delete file {file_id}: {del_response.status_code}"
            )

    except (requests.exceptions.RequestException, ValueError) as file_error:
        logger.warning(f"Error deleting file {file_id}: {file_error}")


def delete_user_storage(user_id: str, company_id: str) -> None:
    """
    Delete all user storage (entire user directory and contents).

    This deletes everything under /users/{user_id}/

    Args:
        user_id: UUID of the user
        company_id: UUID of the company

    Note:
        Failures are logged but don't raise exceptions to avoid blocking user deletion.
    """
    if not is_storage_service_enabled():
        logger.info(
            f"Storage Service disabled - skipping storage deletion for user {user_id}"
        )
        return

    # Since the Storage Service doesn't have a "delete directory" endpoint,
    # we need to list all files and delete them one by one

    from flask import current_app  # pylint: disable=import-outside-toplevel

    # First, try to list all files for this user
    list_url = f"{current_app.config['STORAGE_SERVICE_URL']}/list"

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
    }

    params = {
        "bucket": "users",
        "id": user_id,
        "limit": 1000,  # Get all files
    }

    try:
        logger.info(f"Listing files for user {user_id} to delete")

        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)
        response = requests.get(
            list_url, params=params, headers=headers, timeout=timeout
        )

        if response.status_code == 404:
            logger.info(f"No files found for user {user_id}")
            return

        response.raise_for_status()
        data = response.json()

        files = data.get("data", {}).get("items", [])
        logger.info(f"Found {len(files)} files to delete for user {user_id}")

        # Delete each file
        delete_url = f"{current_app.config['STORAGE_SERVICE_URL']}/delete"

        for file_meta in files:
            file_id = file_meta.get("file_id")
            if file_id:
                _delete_file_from_storage(
                    file_id, delete_url, headers, timeout
                )

        logger.info(f"Finished deleting storage for user {user_id}")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout listing/deleting files for user {user_id}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting user storage: {e}")

    except ValueError as e:
        logger.error(f"JSON parsing error deleting user storage: {e}")
