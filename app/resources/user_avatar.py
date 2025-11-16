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
from app.storage_helper import is_storage_service_enabled
from app.utils import check_access_required, require_jwt_auth


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
        2. Checks if they have an avatar (has_avatar flag)
        3. Calls the Storage Service to get the image using convention-based path
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

        if not user.has_avatar:
            logger.debug(f"User {user_id} has no avatar")
            return {"message": "User has no avatar"}, 404

        # Check if Storage Service integration is enabled
        if not is_storage_service_enabled():
            logger.warning(
                f"Storage Service disabled - cannot retrieve avatar for user {user_id}"
            )
            return {
                "message": "Avatar storage is disabled in this environment"
            }, 503

        # Use convention-based logical_path
        # Avatars are always stored as avatars/{user_id}.{ext}
        # We use a generic extension; Storage Service will handle the correct file
        logical_path = f"avatars/{user_id}.jpg"

        # Get Storage Service URL from environment
        storage_service_url = os.environ.get(
            "STORAGE_SERVICE_URL", "http://storage-service:5000"
        )
        timeout = int(os.environ.get("STORAGE_REQUEST_TIMEOUT", "30"))

        try:
            logger.debug(
                f"Fetching avatar from Storage Service: "
                f"bucket_type=users, bucket_id={user_id}, "
                f"logical_path={logical_path}"
            )

            # Call Storage Service /download/proxy endpoint
            response = requests.get(
                f"{storage_service_url}/download/proxy",
                params={
                    "bucket_type": "users",
                    "bucket_id": user_id,
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
