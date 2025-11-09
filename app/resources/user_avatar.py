"""
module: app.resources.user_avatar

This module defines the Flask-RESTful resource for retrieving user avatars.
It proxies requests to the Storage Service to get the avatar image.
"""

import os
import requests
from flask import Response
from flask_restful import Resource

from app.logger import logger
from app.models.user import User
from app.utils import require_jwt_auth, check_access_required


class UserAvatarResource(Resource):
    """
    Resource for retrieving a user's avatar image.

    This endpoint proxies the avatar image from the Storage Service,
    providing a stable URL that doesn't expire.

    Methods:
        get(user_id): Retrieve avatar image for a specific user
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, user_id):
        """
        Retrieve the avatar image for a user.

        This method:
        1. Looks up the user in the database
        2. Checks if they have an avatar_url (object_key)
        3. Calls the Storage Service to get the image
        4. Streams the image back to the client

        Args:
            user_id (str): The ID of the user whose avatar to retrieve

        Returns:
            Response: The avatar image file stream with appropriate headers
            tuple: Error message and HTTP status code on failure
        """
        user = User.get_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found")
            return {"message": "User not found"}, 404

        if not user.avatar_url:
            logger.debug(f"User {user_id} has no avatar")
            return {"message": "User has no avatar"}, 404

        # Parse the object_key to extract bucket_type, bucket_id, and logical_path
        # Format: users/{user_id}/avatars/{filename}/{version}
        # We need to convert this to the Storage Service format
        object_key = user.avatar_url

        # Extract components from object_key
        # Example: "users/c0fa9ab7-f1c5-46cc-b709-2b9a745332e4/avatars/c0fa9ab7-f1c5-46cc-b709-2b9a745332e4.png/1"
        parts = object_key.split("/")
        if len(parts) < 3 or parts[0] != "users":
            logger.error(f"Invalid object_key format: {object_key}")
            return {"message": "Invalid avatar reference"}, 500

        bucket_type = "users"
        bucket_id = parts[1]  # user_id
        # Reconstruct logical_path: everything after bucket_id, EXCLUDING the version number at the end
        # object_key format: users/{user_id}/avatars/{filename}/{version}
        # logical_path format: avatars/{filename} (no version)
        path_parts = parts[2:]  # ['avatars', 'filename.ext', 'version']
        # Remove the last part if it's a version number
        if len(path_parts) > 0 and path_parts[-1].isdigit():
            path_parts = path_parts[:-1]
        logical_path = "/".join(path_parts)  # avatars/filename.ext

        # Get Storage Service URL from environment
        storage_service_url = os.environ.get(
            "STORAGE_SERVICE_URL", "http://storage-service:5000"
        )
        timeout = int(os.environ.get("STORAGE_REQUEST_TIMEOUT", "30"))

        try:
            logger.debug(
                f"Fetching avatar from Storage Service: bucket_type={bucket_type}, bucket_id={bucket_id}, logical_path={logical_path}"
            )

            # Call Storage Service /download/proxy endpoint with bucket triplet
            response = requests.get(
                f"{storage_service_url}/download/proxy",
                params={
                    "bucket_type": bucket_type,
                    "bucket_id": bucket_id,
                    "logical_path": logical_path,
                },
                headers={
                    "X-User-ID": user_id,
                    "X-Company-ID": user.company_id,
                },
                stream=True,
                timeout=timeout,
            )

            if response.status_code != 200:
                logger.error(
                    f"Storage Service returned {response.status_code}: {response.text}"
                )
                return {
                    "message": "Failed to retrieve avatar"
                }, response.status_code

            # Stream the file back to the client
            logger.info(f"Serving avatar for user {user_id}")
            return Response(
                response.iter_content(chunk_size=8192),
                content_type=response.headers.get(
                    "Content-Type", "image/jpeg"
                ),
                headers={
                    "Content-Disposition": response.headers.get(
                        "Content-Disposition", "inline"
                    ),
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                },
            )

        except requests.exceptions.Timeout:
            logger.error("Timeout fetching avatar from Storage Service")
            return {"message": "Storage service timeout"}, 504

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching avatar: {e}")
            return {"message": "Failed to retrieve avatar"}, 500
