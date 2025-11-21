# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: benjamin@waterfall-project.pro
"""
module: app.resources.customer_logo

This module defines the Flask-RESTful resource for customer logo management.
It provides endpoints for uploading, retrieving, and deleting customer logos.
"""

import requests
from flask import Response, current_app, g, request
from flask_restful import Resource

from app.logger import logger
from app.models import db
from app.models.customer import Customer
from app.storage_helper import (AvatarValidationError, StorageServiceError,
                                delete_customer_logo,
                                upload_customer_logo_via_proxy)
from app.utils import check_access_required, require_jwt_auth


class CustomerLogoResource(Resource):
    """
    Resource for managing customer logos (upload, retrieve, delete).

    Methods:
        post(customer_id): Upload a customer logo
        get(customer_id): Retrieve customer logo image
        delete(customer_id): Delete customer logo
    """

    @require_jwt_auth()
    @check_access_required("update")
    def post(self, customer_id):
        """
        Upload a customer logo.

        Expects multipart/form-data with 'logo' file.

        Args:
            customer_id (str): The ID of the customer

        Returns:
            tuple: Success message and HTTP status code 200/201
            tuple: Error message and HTTP status code on failure
        """
        logger.info(f"Uploading logo for customer {customer_id}")

        customer = Customer.get_by_id(customer_id)
        if not customer:
            logger.warning(f"Customer {customer_id} not found")
            return {"message": "Customer not found"}, 404

        # Verify company_id matches JWT
        jwt_company_id = g.company_id
        if jwt_company_id != customer.company_id:
            logger.warning(
                f"Access denied: JWT company_id {jwt_company_id} "
                f"!= customer company_id {customer.company_id}"
            )
            return {
                "message": "Access denied: cannot manage other company's customer logo"
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
            upload_result = upload_customer_logo_via_proxy(
                customer_id=customer_id,
                company_id=customer.company_id,
                file_data=file_data,
                content_type=content_type,
                filename=filename,
            )

            # Update customer with logo file_id
            customer.set_logo(upload_result["file_id"])
            db.session.commit()

            logger.info(
                f"Logo uploaded for customer {customer_id}: file_id={upload_result['file_id']}"
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
    def get(self, customer_id):
        """
        Retrieve the logo image for a customer.

        Args:
            customer_id (str): The ID of the customer

        Returns:
            Response: The logo image file stream
            tuple: Error message and HTTP status code on failure
        """
        customer = Customer.get_by_id(customer_id)
        if not customer:
            logger.warning(f"Customer {customer_id} not found")
            return {"message": "Customer not found"}, 404

        if not customer.has_logo:
            logger.debug(f"Customer {customer_id} has no logo")
            return {"message": "Customer has no logo"}, 404

        # Check if USE_STORAGE_SERVICE is enabled
        if not current_app.config.get("USE_STORAGE_SERVICE", True):
            logger.warning("Storage Service is disabled")
            return {"message": "Storage Service disabled"}, 404

        # Use convention-based logical_path
        logical_path = f"customers/{customer_id}/logo.png"

        # Get Storage Service config
        storage_service_url = current_app.config["STORAGE_SERVICE_URL"]
        timeout = current_app.config.get("STORAGE_REQUEST_TIMEOUT", 30)

        try:
            logger.debug(
                f"Fetching logo from Storage Service: "
                f"bucket_type=companies, bucket_id={customer.company_id}, "
                f"logical_path={logical_path}"
            )

            response = requests.get(
                f"{storage_service_url}/download/proxy",
                params={
                    "bucket_type": "companies",
                    "bucket_id": customer.company_id,
                    "logical_path": logical_path,
                },
                headers={
                    "X-User-ID": g.user_id,
                    "X-Company-ID": customer.company_id,
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

            logger.info(f"Serving logo for customer {customer_id}")
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
    def delete(self, customer_id):
        """
        Delete customer logo.

        Args:
            customer_id (str): The ID of the customer

        Returns:
            tuple: Success message and HTTP status code 204
            tuple: Error message and HTTP status code on failure
        """
        logger.info(f"Deleting logo for customer {customer_id}")

        customer = Customer.get_by_id(customer_id)
        if not customer:
            logger.warning(f"Customer {customer_id} not found")
            return {"message": "Customer not found"}, 404

        # Verify company_id matches JWT
        jwt_company_id = g.company_id
        if jwt_company_id != customer.company_id:
            logger.warning(
                f"Access denied: JWT company_id {jwt_company_id} "
                f"!= customer company_id {customer.company_id}"
            )
            return {
                "message": "Access denied: cannot delete other company's customer logo"
            }, 403

        if not customer.has_logo:
            return {"message": "Customer has no logo to delete"}, 404

        # Check if USE_STORAGE_SERVICE is enabled
        if not current_app.config.get("USE_STORAGE_SERVICE", True):
            logger.warning("Storage Service is disabled")
            # Still clear the flag in database
            customer.remove_logo()
            db.session.commit()
            return {"message": "Logo reference removed"}, 204

        # Delete from Storage Service (if file_id is available)
        if customer.logo_file_id:
            try:
                delete_customer_logo(customer_id, customer.logo_file_id)
            except Exception as e:  # pylint: disable=broad-except
                # Catch all exceptions to ensure database cleanup happens
                logger.warning(f"Failed to delete logo from storage: {e}")
                # Continue anyway to clear database

        # Clear logo reference in database
        customer.remove_logo()
        db.session.commit()

        logger.info(f"Logo deleted for customer {customer_id}")
        return {"message": "Logo deleted successfully"}, 204
