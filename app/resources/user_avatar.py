"""
module: app.resources.user_avatar

This module defines the Flask-RESTful resource for user avatar management.
It provides endpoints for uploading, retrieving, and deleting user avatars.
"""

import requests
from flask import Response, current_app, g, request
from flask_restful import Resource

from app.logger import logger
from app.models import db
from app.models.user import User
from app.storage_helper import (AvatarValidationError, StorageServiceError,
                                delete_avatar, is_storage_service_enabled,
                                upload_avatar_via_proxy)
from app.utils import check_access_required, require_jwt_auth


class UserAvatarResource(Resource):
    """
    Resource for managing user avatars (upload, retrieve, delete).

    Methods:
        post(user_id): Upload a user avatar
        get(user_id): Retrieve user avatar image
        delete(user_id): Delete user avatar
    """

    @require_jwt_auth()
    @check_access_required("update")
    def post(self, user_id):
        """
        Upload a user avatar.

        Expects multipart/form-data with 'avatar' file.

        Args:
            user_id (str): The ID of the user

        Returns:
            tuple: Success message and HTTP status code 200/201
            tuple: Error message and HTTP status code on failure
        """
        logger.info(f"Uploading avatar for user {user_id}")

        user = User.get_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found")
            return {"message": "User not found"}, 404

        # Verify user_id matches JWT or user has permission
        jwt_data = getattr(g, "jwt_data", {})
        jwt_user_id = jwt_data.get("user_id")

        # Users can only upload their own avatar (unless admin - future enhancement)
        if jwt_user_id != user_id:
            logger.warning(
                f"Access denied: JWT user_id {jwt_user_id} != {user_id}"
            )
            return {
                "message": "Access denied: cannot manage other user's avatar"
            }, 403

        # Get uploaded file
        if "avatar" not in request.files:
            return {"message": "No avatar file provided"}, 400

        # Check if USE_STORAGE_SERVICE is enabled
        if not current_app.config.get("USE_STORAGE_SERVICE", True):
            logger.warning(
                "Storage Service is disabled, skipping avatar upload"
            )
            return {"message": "Storage Service disabled"}, 503

        avatar_file = request.files["avatar"]
        company_id = jwt_data.get("company_id")

        try:
            file_data = avatar_file.read()
            content_type = avatar_file.content_type or "image/jpeg"
            filename = avatar_file.filename or "avatar.jpg"

            # Upload to Storage Service
            upload_result = upload_avatar_via_proxy(
                user_id=user_id,
                company_id=company_id,
                file_data=file_data,
                content_type=content_type,
                filename=filename,
            )

            # Update user with avatar file_id
            user.set_avatar(upload_result["file_id"])
            db.session.commit()

            logger.info(
                f"Avatar uploaded for user {user_id}: file_id={upload_result['file_id']}"
            )

            return {
                "message": "Avatar uploaded successfully",
                "avatar_file_id": upload_result["file_id"],
                "has_avatar": True,
            }, 201

        except AvatarValidationError as e:
            logger.warning(f"Avatar validation failed: {e}")
            return {"message": str(e)}, 400

        except StorageServiceError as e:
            logger.error(f"Storage service error: {e}")
            return {"message": "Failed to upload avatar"}, 500

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
        # Avatars sont toujours stockés comme avatars/{user_id}.png
        # L'extension .png est normalisée (voir storage_helper.py)
        # Le vrai format (JPEG, PNG, WebP, etc.) est dans le Content-Type HTTP
        # que le Storage Service retourne au download (le navigateur lit ça, pas l'extension)
        logical_path = f"avatars/{user_id}.png"

        # Get Storage Service config
        storage_service_url = current_app.config["STORAGE_SERVICE_URL"]
        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)

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

    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, user_id):
        """
        Delete user avatar.

        Args:
            user_id (str): The ID of the user

        Returns:
            tuple: Success message and HTTP status code 204
            tuple: Error message and HTTP status code on failure
        """
        logger.info(f"Deleting avatar for user {user_id}")

        user = User.get_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found")
            return {"message": "User not found"}, 404

        # Verify user_id matches JWT or user has permission
        jwt_data = getattr(g, "jwt_data", {})
        jwt_user_id = jwt_data.get("user_id")

        # Users can only delete their own avatar (unless admin - future enhancement)
        if jwt_user_id != user_id:
            logger.warning(
                f"Access denied: JWT user_id {jwt_user_id} != {user_id}"
            )
            return {
                "message": "Access denied: cannot delete other user's avatar"
            }, 403

        if not user.has_avatar:
            return {"message": "User has no avatar to delete"}, 404

        # Check if USE_STORAGE_SERVICE is enabled
        if not current_app.config.get("USE_STORAGE_SERVICE", True):
            logger.warning("Storage Service is disabled")
            # Still clear the flag in database
            user.remove_avatar()
            db.session.commit()
            return {"message": "Avatar reference removed"}, 204

        # Delete from Storage Service (if file_id is available)
        company_id = jwt_data.get("company_id")
        if user.avatar_file_id:
            try:
                delete_avatar(user_id, company_id, user.avatar_file_id)
            except Exception as e:  # pylint: disable=broad-except
                # Catch all exceptions to ensure database cleanup happens
                logger.warning(f"Failed to delete avatar from storage: {e}")
                # Continue anyway to clear database

        # Clear avatar reference in database
        user.remove_avatar()
        db.session.commit()

        logger.info(f"Avatar deleted for user {user_id}")
        return {"message": "Avatar deleted successfully"}, 204
