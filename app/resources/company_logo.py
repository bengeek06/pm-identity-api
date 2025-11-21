"""
module: app.resources.company_logo

This module defines the Flask-RESTful resource for company logo management.
It provides endpoints for uploading, retrieving, and deleting company logos.
"""

import requests
from flask import Response, current_app, g, request
from flask_restful import Resource

from app.logger import logger
from app.models import db
from app.models.company import Company
from app.storage_helper import (AvatarValidationError, StorageServiceError,
                                delete_logo, upload_logo_via_proxy)
from app.utils import check_access_required, require_jwt_auth


class CompanyLogoResource(Resource):
    """
    Resource for managing company logos (upload, retrieve, delete).

    Methods:
        post(company_id): Upload a company logo
        get(company_id): Retrieve company logo image
        delete(company_id): Delete company logo
    """

    @require_jwt_auth()
    @check_access_required("update")
    def post(self, company_id):
        """
        Upload a company logo.

        Expects multipart/form-data with 'logo' file.

        Args:
            company_id (str): The ID of the company

        Returns:
            tuple: Success message and HTTP status code 200/201
            tuple: Error message and HTTP status code on failure
        """
        logger.info(f"Uploading logo for company {company_id}")

        company = Company.get_by_id(company_id)
        if not company:
            logger.warning(f"Company {company_id} not found")
            return {"message": "Company not found"}, 404

        # Verify company_id matches JWT
        jwt_company_id = g.company_id
        if jwt_company_id != company_id:
            logger.warning(
                f"Access denied: JWT company_id {jwt_company_id} != {company_id}"
            )
            return {
                "message": "Access denied: cannot manage other company's logo"
            }, 403

        # Get uploaded file
        if "logo" not in request.files:
            return {"message": "No logo file provided"}, 400

        # Check if USE_STORAGE_SERVICE is enabled
        if not current_app.config.get("USE_STORAGE_SERVICE", True):
            logger.warning("Storage Service is disabled, skipping logo upload")
            return {"message": "Storage Service disabled"}, 503

        logo_file = request.files["logo"]

        try:
            file_data = logo_file.read()
            content_type = logo_file.content_type or "image/png"
            filename = logo_file.filename or "logo.png"

            # Upload to Storage Service
            upload_result = upload_logo_via_proxy(
                company_id=company_id,
                user_id=g.user_id,  # User ID for auth
                file_data=file_data,
                content_type=content_type,
                filename=f"logo_{filename}",
            )

            # Update company with logo file_id
            company.set_logo(upload_result["file_id"])
            db.session.commit()

            logger.info(
                f"Logo uploaded for company {company_id}: file_id={upload_result['file_id']}"
            )

            return {
                "message": "Logo uploaded successfully",
                "logo_file_id": upload_result["file_id"],
                "has_logo": True,
            }, 201

        except AvatarValidationError as e:
            logger.warning(f"Logo validation failed: {e}")
            return {"message": str(e)}, 400

        except StorageServiceError as e:
            logger.error(f"Storage service error: {e}")
            return {"message": "Failed to upload logo"}, 500

    @require_jwt_auth()
    @check_access_required("read")
    def get(self, company_id):
        """
        Retrieve the logo image for a company.

        Args:
            company_id (str): The ID of the company

        Returns:
            Response: The logo image file stream
            tuple: Error message and HTTP status code on failure
        """
        company = Company.get_by_id(company_id)
        if not company:
            logger.warning(f"Company {company_id} not found")
            return {"message": "Company not found"}, 404

        if not company.has_logo:
            logger.debug(f"Company {company_id} has no logo")
            return {"message": "Company has no logo"}, 404

        # Check if USE_STORAGE_SERVICE is enabled
        if not current_app.config.get("USE_STORAGE_SERVICE", True):
            logger.warning("Storage Service is disabled")
            return {"message": "Storage Service disabled"}, 404

        # Use convention-based logical_path
        # Logos sont toujours stockés comme logos/{company_id}.png
        # L'extension .png est normalisée (voir storage_helper.py)
        # Le vrai format (JPEG, PNG, WebP, etc.) est dans le Content-Type HTTP
        # que le Storage Service retourne au download (le navigateur lit ça, pas l'extension)
        logical_path = f"logos/{company_id}.png"

        # Get Storage Service config
        storage_service_url = current_app.config["STORAGE_SERVICE_URL"]
        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)

        try:
            logger.debug(
                f"Fetching logo from Storage Service: "
                f"bucket_type=companies, bucket_id={company_id}, "
                f"logical_path={logical_path}"
            )

            response = requests.get(
                f"{storage_service_url}/download/proxy",
                params={
                    "bucket_type": "companies",
                    "bucket_id": company_id,
                    "logical_path": logical_path,
                },
                headers={
                    "X-User-ID": company_id,
                    "X-Company-ID": company_id,
                },
                stream=True,
                timeout=timeout,
            )

            if response.status_code != 200:
                logger.error(
                    f"Storage Service returned {response.status_code}: {response.text}"
                )
                return {
                    "message": "Failed to retrieve logo"
                }, response.status_code

            logger.info(f"Serving logo for company {company_id}")
            return Response(
                response.iter_content(chunk_size=8192),
                content_type=response.headers.get("Content-Type", "image/png"),
                headers={
                    "Content-Disposition": response.headers.get(
                        "Content-Disposition", "inline"
                    ),
                    "Cache-Control": "public, max-age=3600",
                },
            )

        except requests.exceptions.Timeout:
            logger.error("Timeout fetching logo from Storage Service")
            return {"message": "Storage service timeout"}, 504

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching logo: {e}")
            return {"message": "Failed to retrieve logo"}, 500

    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, company_id):
        """
        Delete company logo.

        Args:
            company_id (str): The ID of the company

        Returns:
            tuple: Success message and HTTP status code 204
            tuple: Error message and HTTP status code on failure
        """
        logger.info(f"Deleting logo for company {company_id}")

        company = Company.get_by_id(company_id)
        if not company:
            logger.warning(f"Company {company_id} not found")
            return {"message": "Company not found"}, 404

        # Verify company_id matches JWT
        jwt_company_id = g.company_id
        if jwt_company_id != company_id:
            logger.warning(
                f"Access denied: JWT company_id {jwt_company_id} != {company_id}"
            )
            return {
                "message": "Access denied: cannot delete other company's logo"
            }, 403

        if not company.has_logo:
            return {"message": "Company has no logo to delete"}, 404

        # Check if USE_STORAGE_SERVICE is enabled
        if not current_app.config.get("USE_STORAGE_SERVICE", True):
            logger.warning("Storage Service is disabled")
            # Still clear the flag in database
            company.remove_logo()
            db.session.commit()
            return {"message": "Logo reference removed"}, 204

        # Delete from Storage Service (if file_id is available)
        if company.logo_file_id:
            # Get user_id from JWT for auth
            jwt_user_id = g.user_id

            try:
                delete_logo(company_id, jwt_user_id, company.logo_file_id)
            except Exception as e:  # pylint: disable=broad-except
                # Catch all exceptions to ensure database cleanup happens
                logger.warning(f"Failed to delete logo from storage: {e}")
                # Continue anyway to clear database

        # Clear logo reference in database
        company.remove_logo()
        db.session.commit()

        logger.info(f"Logo deleted for company {company_id}")
        return {"message": "Logo deleted successfully"}, 204
