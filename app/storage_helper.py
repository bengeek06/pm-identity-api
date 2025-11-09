"""
storage_helper.py
=================

Helper functions for interacting with the Storage Service.
Provides avatar upload/delete functionality for the Identity Service.
"""

import os
import requests

from app.logger import logger

# Configuration
STORAGE_SERVICE_URL = os.getenv(
    "STORAGE_SERVICE_URL", "http://storage-service:5000"
)
REQUEST_TIMEOUT = int(os.getenv("STORAGE_REQUEST_TIMEOUT", "30"))
MAX_AVATAR_SIZE = int(os.getenv("MAX_AVATAR_SIZE_MB", "5")) * 1024 * 1024

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
    file_data: bytes, content_type: str, max_size: int = MAX_AVATAR_SIZE
) -> None:
    """
    Validate an avatar file.

    Args:
        file_data: Binary file data
        content_type: MIME type of the file
        max_size: Maximum size in bytes

    Raises:
        AvatarValidationError: If validation fails
    """
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


def upload_avatar_via_proxy(
    user_id: str,
    company_id: str,
    file_data: bytes,
    content_type: str,
    filename: str,
) -> str:
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
        str: The object_key to store in the database (avatar_url field)

    Raises:
        AvatarValidationError: If validation fails
        StorageServiceError: If upload fails
    """
    # Validate the file
    validate_avatar(file_data, content_type)

    # Prepare the logical path
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    logical_path = f"avatars/{user_id}.{extension}"
    logger.debug(f"Logical path for avatar: {logical_path}")

    url = f"{STORAGE_SERVICE_URL}/upload/proxy"

    headers = {
        "X-User-ID": user_id,
        "X-Company-ID": company_id,
    }

    # Prepare multipart/form-data
    files = {
        "file": (filename, file_data, content_type),
    }

    data = {
        "bucket_type": "users",
        "bucket_id": user_id,
        "logical_path": logical_path,
    }
    logger.debug(f"Uploading avatar for user {user_id} to {url}")

    try:
        logger.info(
            f"Uploading avatar for user {user_id}: {len(file_data)} bytes"
        )

        response = requests.post(
            url,
            files=files,
            data=data,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
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

        # The object_key can be either at root level or in 'data' object
        object_key = result.get("object_key")
        if not object_key and "data" in result:
            object_key = result["data"].get("object_key")

        if not object_key:
            raise StorageServiceError(
                f"Storage Service did not return object_key. Response: {result}"
            )

        logger.info(f"Avatar uploaded successfully: {object_key}")
        logger.debug(f"object_key length: {len(object_key)}")
        return object_key

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
    if not file_id:
        logger.warning("No file_id provided for deletion")
        return

    url = f"{STORAGE_SERVICE_URL}/delete"

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

        response = requests.delete(
            url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
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
    url = f"{STORAGE_SERVICE_URL}/upload/proxy"

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

            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
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
    # Since the Storage Service doesn't have a "delete directory" endpoint,
    # we need to list all files and delete them one by one

    # First, try to list all files for this user
    list_url = f"{STORAGE_SERVICE_URL}/list"

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

        response = requests.get(
            list_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 404:
            logger.info(f"No files found for user {user_id}")
            return

        response.raise_for_status()
        data = response.json()

        files = data.get("data", {}).get("items", [])
        logger.info(f"Found {len(files)} files to delete for user {user_id}")

        # Delete each file
        delete_url = f"{STORAGE_SERVICE_URL}/delete"

        for file_meta in files:
            file_id = file_meta.get("file_id")
            if not file_id:
                continue

            try:
                delete_payload = {
                    "file_id": file_id,
                    "physical": True,  # Permanent deletion
                }

                del_response = requests.delete(
                    delete_url,
                    json=delete_payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )

                if del_response.status_code in (200, 204, 404):
                    logger.debug(f"Deleted file {file_id}")
                else:
                    logger.warning(
                        f"Failed to delete file {file_id}: {del_response.status_code}"
                    )

            except (requests.exceptions.RequestException, ValueError) as file_error:
                logger.warning(f"Error deleting file {file_id}: {file_error}")
                # Continue with next file

        logger.info(f"Finished deleting storage for user {user_id}")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout listing/deleting files for user {user_id}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting user storage: {e}")

    except ValueError as e:
        logger.error(f"JSON parsing error deleting user storage: {e}")
