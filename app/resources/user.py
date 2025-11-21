# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
module: app.resources.user

This module defines the Flask-RESTful resources for basic User CRUD operations
in the Identity Service API.

It provides endpoints for listing, creating, retrieving, updating, partially
updating, and deleting users. The resources use Marshmallow schemas for
validation and serialization, and handle database errors gracefully.

For related user operations, see:
- app.resources.user_position: Users by position
- app.resources.user_roles: User role assignments (RBAC)
- app.resources.user_policies: User policy aggregation (RBAC)
- app.resources.user_permissions: User permission aggregation (RBAC)
- app.resources.user_auth: User authentication operations
"""

from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.constants import (LOG_DATABASE_ERROR, LOG_INTEGRITY_ERROR,
                           LOG_VALIDATION_ERROR, MSG_DATABASE_ERROR,
                           MSG_INTEGRITY_ERROR, MSG_VALIDATION_ERROR)
from app.logger import logger
from app.models import db
from app.models.company import Company
from app.models.user import User
from app.schemas.user_schema import UserSchema
from app.storage_helper import (AvatarValidationError, StorageServiceError,
                                create_user_directories, delete_user_storage,
                                upload_avatar_via_proxy)
from app.utils import check_access_required, require_jwt_auth

# Content type constants
CONTENT_TYPE_MULTIPART = "multipart/form-data"


# Helper functions for user operations
def _validate_avatar_url_field(avatar_url_value, context="POST"):
    """Log warning if avatar_url is sent by frontend (this is a bug)."""
    is_base64 = (
        avatar_url_value.startswith("data:image/")
        if avatar_url_value
        else False
    )
    logger.warning(
        f"[{context}] Frontend sent avatar_url - THIS IS A BUG! "
        f"Length: {len(avatar_url_value)} chars, "
        f"Is base64 data URI: {is_base64}, "
        f"Preview: {avatar_url_value[:50]}... "
        f"EXPECTED: Frontend should send file via "
        f"'avatar' field in {CONTENT_TYPE_MULTIPART}, "
        f"NOT avatar_url. The backend manages avatar_url "
        f"after upload to Storage Service."
    )


def _parse_request_data(is_multipart, context="POST"):
    """Parse request data from multipart or JSON."""
    if is_multipart:
        # Check if avatar_url is in multipart form data (this is a bug)
        if "avatar_url" in request.form:
            _validate_avatar_url_field(request.form["avatar_url"], context)

        # Get form data but exclude file fields and avatar_url
        json_data = {
            k: v
            for k, v in request.form.items()
            if k not in ("avatar", "avatar_url")
        }
    else:
        json_data = request.get_json() or {}
        # Remove avatar_url from JSON data if present
        if "avatar_url" in json_data:
            _validate_avatar_url_field(json_data["avatar_url"], context)
            json_data.pop("avatar_url", None)

    return json_data


def _handle_avatar_upload(user):
    """Handle avatar upload if present in request."""
    if "avatar" not in request.files:
        return

    avatar_file = request.files["avatar"]
    try:
        file_data = avatar_file.read()
        content_type = avatar_file.content_type or "image/jpeg"
        filename = avatar_file.filename or "avatar.jpg"

        upload_result = upload_avatar_via_proxy(
            user_id=str(user.id),
            file_data=file_data,
            content_type=content_type,
            filename=filename,
        )

        user.set_avatar(upload_result["file_id"])
        db.session.commit()
        logger.info(
            f"Avatar uploaded for new user {user.id}: file_id={upload_result['file_id']}"
        )

    except AvatarValidationError as e:
        logger.warning(f"Avatar validation failed: {e}")
        # Don't fail user creation, just log the warning

    except StorageServiceError as e:
        logger.error(f"Storage service error: {e}")
        # Don't fail user creation, just log the error


def _create_user_storage(user_id):
    """Create user directory structure in Storage Service."""
    try:
        create_user_directories(user_id=str(user_id))
        logger.info(f"User directories created for {user_id}")
    except StorageServiceError as e:
        logger.warning(f"Failed to create user directories: {e}")
        # Don't fail user creation if directory creation fails


def _handle_avatar_upload_for_update(user):
    """Handle avatar upload for PUT/PATCH operations."""
    if "avatar" not in request.files:
        return None

    avatar_file = request.files["avatar"]
    try:
        # Upload new avatar (Storage Service handles versioning automatically)
        file_data = avatar_file.read()
        content_type = avatar_file.content_type or "image/jpeg"
        filename = avatar_file.filename or "avatar.jpg"

        upload_result = upload_avatar_via_proxy(
            user_id=str(user.id),
            file_data=file_data,
            content_type=content_type,
            filename=filename,
        )

        logger.info(
            f"Avatar updated for user {user.id}: file_id={upload_result['file_id']}"
        )
        return upload_result["file_id"]

    except AvatarValidationError as e:
        logger.warning(f"Avatar validation failed: {e}")
        raise

    except StorageServiceError as e:
        logger.error(f"Storage service error: {e}")
        raise


def _parse_multipart_data_with_debug(context="PATCH"):
    """Parse multipart data with detailed debug logging."""
    logger.debug(f"[{context}] request.form keys: {list(request.form.keys())}")
    logger.debug(
        f"[{context}] request.files keys: {list(request.files.keys())}"
    )

    for key in request.form.keys():
        value = request.form[key]
        logger.debug(
            f"[{context}] form field '{key}': "
            f"length={len(value) if value else 0}, "
            f"preview={value[:100] if value and len(value) > 100 else value}"
        )

    # Check if avatar_url is in multipart form data (this is a bug)
    if "avatar_url" in request.form:
        _validate_avatar_url_field(request.form["avatar_url"], context)

    # Get form data but exclude file fields and avatar_url
    return {
        k: v
        for k, v in request.form.items()
        if k not in ("avatar", "avatar_url")
    }


def _parse_patch_request_data():
    """Parse request data for PATCH operation with debug logging."""
    logger.debug(f"[PATCH] Content-Type: {request.content_type}")
    logger.debug(f"[PATCH] Mimetype: {request.mimetype}")
    logger.debug(
        f"[PATCH] Has form: {bool(request.form)}, Has files: {bool(request.files)}"
    )

    # Check if request has multipart data
    has_form_data = len(request.form) > 0 or len(request.files) > 0
    is_multipart_content = (
        request.content_type and "multipart" in request.content_type
    ) or (request.mimetype and "multipart" in request.mimetype)

    if has_form_data or is_multipart_content:
        return _parse_multipart_data_with_debug(context="PATCH")

    # Parse as JSON
    json_data = request.get_json(force=True, silent=True) or {}
    logger.debug(f"[PATCH] Parsed JSON data: {bool(json_data)}")

    # Remove avatar_url from JSON data if present
    if "avatar_url" in json_data:
        _validate_avatar_url_field(json_data["avatar_url"], "PATCH")
        json_data.pop("avatar_url", None)

    logger.debug(f"[PATCH] json_data after filtering: {json_data}")
    return json_data


def _process_avatar_upload_for_patch(user):
    """
    Handle avatar upload for PATCH operation.

    Returns:
        str or None: File ID if avatar was uploaded, None otherwise.

    Raises:
        ValidationError: If upload fails.
    """
    try:
        return _handle_avatar_upload_for_update(user)
    except AvatarValidationError as e:
        raise ValidationError({"avatar": [str(e)]}) from e
    except StorageServiceError as exc:
        raise ValidationError({"avatar": ["Failed to upload avatar"]}) from exc


class UserListResource(Resource):
    """
    Resource for handling user list operations.

    Methods:
        get():
            Retrieve all users from the database.

        post():
            Create a new user with the provided data.
    """

    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """
        Get all users from the authenticated user's company.

        Supports optional filtering, pagination, and sorting.

        Query Parameters:
            email (str, optional): Filter by exact email match
            page (int, optional): Page number (default: 1, min: 1)
            limit (int, optional): Items per page (default: 50, max: 1000)
            sort (str, optional): Sort by (created_at, updated_at, email)
            order (str, optional): Sort order (asc, desc, default: asc)

        Returns:
            tuple: Paginated response with data and metadata, HTTP 200
        """
        logger.info("Fetching all users")
        try:
            # Get company_id from JWT data stored in g by the decorator
            company_id = g.company_id

            if not company_id:
                logger.error("company_id missing in JWT")
                return {"message": "company_id missing in JWT"}, 400

            # Filter users by company_id to only return users from the same company
            query = User.query.filter_by(company_id=company_id)

            # Apply email filter if provided
            email = request.args.get("email")
            if email:
                query = query.filter_by(email=email)

            # Pagination parameters
            page = request.args.get("page", 1, type=int)
            limit = request.args.get("limit", 50, type=int)

            # Validate and constrain pagination params
            page = max(1, page)
            limit = min(max(1, limit), 1000)

            # Sorting parameters
            sort_field = request.args.get("sort", "created_at")
            sort_order = request.args.get("order", "asc")

            # Validate sort field
            allowed_sorts = ["created_at", "updated_at", "email"]
            if sort_field not in allowed_sorts:
                sort_field = "created_at"

            # Apply sorting
            if sort_order == "desc":
                query = query.order_by(getattr(User, sort_field).desc())
            else:
                query = query.order_by(getattr(User, sort_field).asc())

            # Execute pagination
            paginated = query.paginate(
                page=page, per_page=limit, error_out=False
            )

            schema = UserSchema(many=True)
            # Manually exclude sensitive fields after dump
            result_data = schema.dump(paginated.items)
            for user in result_data:
                user.pop("hashed_password", None)

            return {
                "data": result_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": paginated.total,
                    "pages": paginated.pages,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }, 200
        except SQLAlchemyError as e:
            logger.error("Error fetching users: %s", str(e))
            return {"message": "Error fetching users"}, 500

    @require_jwt_auth()
    @check_access_required("create")
    def post(self):
        """
        Create a new user.

        Expects:
            JSON payload with at least 'email', 'password', 'first_name',
            'last_name'.
            company_id is automatically extracted from JWT token.
            Optional: multipart/form-data with 'avatar' file.

        Returns:
            tuple: The serialized created user and HTTP status code 201 on
                   success.
            tuple: Error message and HTTP status code 400 or 500 on failure.
        """
        logger.info("Creating a new user")

        # Handle multipart/form-data or JSON
        is_multipart = (
            request.content_type
            and CONTENT_TYPE_MULTIPART in request.content_type
        ) or (request.mimetype and CONTENT_TYPE_MULTIPART in request.mimetype)

        # Parse request data
        json_data = _parse_request_data(is_multipart, context="POST")

        user_schema = UserSchema(session=db.session)

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            user = user_schema.load(json_data)
            # Assign company_id from JWT after load
            user.company_id = g.company_id

            # Handle nullable company_id for superuser creation
            if user.company_id:
                company = Company.get_by_id(user.company_id)
                if not company:
                    logger.warning(
                        "Company with ID %s not found", user.company_id
                    )
                    return {"message": "Company not found"}, 404
                user.company = company
            # If company_id is None, this is a superuser creation
            db.session.add(user)
            db.session.commit()

            # Create user directory structure in Storage Service
            _create_user_storage(user.id)

            # Handle avatar upload if present
            _handle_avatar_upload(user)

            return user_schema.dump(user), 201
        except ValidationError as e:
            logger.error(LOG_VALIDATION_ERROR, e.messages)
            return {"message": MSG_VALIDATION_ERROR, "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(e))
            return {"message": MSG_INTEGRITY_ERROR}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500


class UserResource(Resource):
    """
    Resource for handling individual user operations.

    Methods:
        get(user_id):
            Retrieve a user by ID.

        put(user_id):
            Update a user by ID.

        patch(user_id):
            Partially update a user by ID.

        delete(user_id):
            Delete a user by ID.
    """

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, user_id):
        """
        Get a user by ID.

        Args:
            user_id (str): The ID of the user to retrieve.

        Returns:
            tuple: The serialized user and HTTP status code 200 on success.
                   HTTP status code 404 if the user is not found.
        """
        logger.info("Fetching user with ID %s", user_id)

        user = User.get_by_id(user_id)
        if not user:
            return {"message": "User not found"}, 404

        schema = UserSchema()
        return schema.dump(user), 200

    @require_jwt_auth()
    @check_access_required("update")
    def put(self, user_id):
        """
        Update a user by ID.

        Expects:
            JSON payload with fields to update.
            Optional: multipart/form-data with 'avatar' file.

        Args:
            user_id (str): The ID of the user to update.

        Returns:
            tuple: The serialized updated user and HTTP status code 200 on
                   success.
                   HTTP status code 404 if the user is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info("Updating user with ID %s", user_id)

        # Handle multipart/form-data or JSON
        is_multipart = (
            request.content_type
            and CONTENT_TYPE_MULTIPART in request.content_type
        ) or (request.mimetype and CONTENT_TYPE_MULTIPART in request.mimetype)

        # Parse request data
        json_data = _parse_request_data(is_multipart, context="PUT")

        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        user_schema = UserSchema(session=db.session, context={"user": user})

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            # Handle avatar upload if present
            uploaded_file_id = None
            try:
                uploaded_file_id = _handle_avatar_upload_for_update(user)
            except AvatarValidationError as e:
                return {"message": str(e)}, 400
            except StorageServiceError:
                return {"message": "Failed to upload avatar"}, 500

            updated_user = user_schema.load(json_data, instance=user)

            # Update avatar using helper method
            if uploaded_file_id:
                updated_user.set_avatar(uploaded_file_id)

            db.session.commit()
            return user_schema.dump(updated_user), 200
        except ValidationError as e:
            logger.error(f"Validation error: {e.messages}")
            return {"message": "Validation error", "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error: {str(e.orig)}")
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500

    @require_jwt_auth()
    @check_access_required("update")
    def patch(self, user_id):
        """
        Partially update a user by ID.

        Expects:
            JSON payload with fields to update.
            Optional: multipart/form-data with 'avatar' file.

        Args:
            user_id (str): The ID of the user to update.

        Returns:
            tuple: The serialized updated user and HTTP status code 200 on
                   success.
                   HTTP status code 404 if the user is not found.
                   HTTP status code 400 for validation errors.
        """
        logger.info(f"Partially updating user with ID {user_id}")

        # Parse request data with debug logging
        json_data = _parse_patch_request_data()

        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        user_schema = UserSchema(
            session=db.session, partial=True, context={"user": user}
        )

        if "password" in json_data:
            json_data["hashed_password"] = generate_password_hash(
                json_data["password"]
            )
            del json_data["password"]

        try:
            # Handle avatar upload if present
            uploaded_file_id = _process_avatar_upload_for_patch(user)

            # Company_id modification is prevented by schema validation
            logger.debug(f"[PATCH] json_data before schema.load: {json_data}")
            updated_user = user_schema.load(
                json_data, instance=user, partial=True
            )

            # Update avatar using helper method
            if uploaded_file_id:
                updated_user.set_avatar(uploaded_file_id)
                logger.debug(
                    f"[PATCH] Set avatar file_id on user object: {uploaded_file_id}"
                )

            db.session.commit()
            return user_schema.dump(updated_user), 200
        except ValidationError as e:
            logger.error(LOG_VALIDATION_ERROR, e.messages)
            return {"message": MSG_VALIDATION_ERROR, "errors": e.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error(LOG_INTEGRITY_ERROR, str(e))
            return {"message": MSG_INTEGRITY_ERROR}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500

    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, user_id):
        """
        Delete a user by ID.

        Also deletes all user storage (avatar and workspace) from the Storage Service.

        Args:
            user_id (str): The ID of the user to delete.

        Returns:
            tuple: Message and HTTP status code 204 on success,
                   or error message and code on failure.
        """
        logger.info("Deleting user with ID %s", user_id)

        user = User.get_by_id(user_id)
        if not user:
            logger.warning("User with ID %s not found", user_id)
            return {"message": "User not found"}, 404

        # Delete all user storage from Storage Service
        try:
            delete_user_storage(user_id=str(user.id))
            logger.info(f"User storage deleted for {user.id}")
        except (StorageServiceError, ValueError) as e:
            # Log but don't fail user deletion if storage deletion fails
            logger.warning(f"Failed to delete user storage: {e}")

        try:
            db.session.delete(user)
            db.session.commit()
            return {"message": "User deleted successfully"}, 204
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(LOG_DATABASE_ERROR, str(e))
            return {"message": MSG_DATABASE_ERROR}, 500
