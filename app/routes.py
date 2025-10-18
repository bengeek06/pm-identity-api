"""
routes.py
---------

This module is responsible for registering the REST API routes for the
Flask application.
It links each endpoint to its corresponding resource class.

Functions:
    - register_routes(app): Register all REST API endpoints on the Flask app.
"""

from flask_restful import Api
from app.logger import logger
from app.resources.version import VersionResource
from app.resources.config import ConfigResource
from app.resources.company import CompanyListResource, CompanyResource
from app.resources.customer import CustomerListResource, CustomerResource
from app.resources.organization_unit import (
    OrganizationUnitListResource,
    OrganizationUnitResource,
    OrganizationUnitChildrenResource,
)
from app.resources.position import (
    PositionListResource,
    PositionResource,
    OrganizationUnitPositionsResource,
)
from app.resources.subcontractor import (
    SubcontractorListResource,
    SubcontractorResource,
)
from app.resources.user import (
    UserListResource,
    UserResource,
    UserPositionResource,
    VerifyPasswordResource,
    UserRolesResource,
)
from app.resources.init_db import InitDBResource
from app.resources.health import HealthResource


def register_routes(app):
    """
    Register the REST API routes on the Flask application.

    Args:
        app (Flask): The Flask application instance.

    This function creates a Flask-RESTful Api instance, adds the resource
    endpoints for all entities (dummy, company, customer, organization unit,
    position, subcontractor, user, etc.), and logs the successful registration
    of routes.
    """
    api = Api(app)

    api.add_resource(VersionResource, "/version")
    api.add_resource(ConfigResource, "/config")
    api.add_resource(InitDBResource, "/init-db")
    api.add_resource(HealthResource, "/health")

    api.add_resource(CompanyListResource, "/companies")
    api.add_resource(CompanyResource, "/companies/<string:company_id>")

    api.add_resource(CustomerListResource, "/customers")
    api.add_resource(CustomerResource, "/customers/<string:customer_id>")

    api.add_resource(OrganizationUnitListResource, "/organization_units")
    api.add_resource(
        OrganizationUnitResource, "/organization_units/<string:unit_id>"
    )
    api.add_resource(
        OrganizationUnitChildrenResource,
        "/organization_units/<string:unit_id>/children",
    )

    api.add_resource(PositionListResource, "/positions")
    api.add_resource(PositionResource, "/positions/<string:position_id>")
    api.add_resource(
        OrganizationUnitPositionsResource,
        "/organization_units/<string:unit_id>/positions",
    )

    api.add_resource(SubcontractorListResource, "/subcontractors")
    api.add_resource(
        SubcontractorResource, "/subcontractors/<string:subcontractor_id>"
    )

    api.add_resource(UserListResource, "/users")
    api.add_resource(UserResource, "/users/<string:user_id>")
    api.add_resource(UserRolesResource, "/users/<string:user_id>/roles")
    api.add_resource(
        UserPositionResource, "/positions/<string:position_id>/users"
    )
    api.add_resource(VerifyPasswordResource, "/verify_password")

    logger.info("Routes registered successfully.")
