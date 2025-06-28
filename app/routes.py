"""
routes.py
-----------
Routes for the Flask application.
# This module is responsible for registering the routes of the REST API
# and linking them to the corresponding resources.
"""
from flask_restful import Api
from app.logger import logger
from app.resources.dummy import DummyResource, DummyListResource
from app.resources.version import VersionResource
from app.resources.config import ConfigResource
from app.resources.export_to import ExportCSVResource
from app.resources.import_from import ImportCSVResource, ImportJSONResource
from app.resources.company import CompanyListResource, CompanyResource
from app.resources.customer import CustomerListResource, CustomerResource
from app.resources.organization_unit import OrganizationUnitListResource, OrganizationUnitResource, OrganizationUnitChildrenResource
from app.resources.position import PositionListResource, PositionResource, OrganizationUnitPositionsResource
from app.resources.subcontractor import SubcontractorListResource, SubcontractorResource
from app.resources.user import (
    UserListResource,
    UserResource,
    UserCompanyResource,
    UserPositionResource,
    VerifyPasswordResource
)


def register_routes(app):
    """
    Register the REST API routes on the Flask application.

    Args:
        app (Flask): The Flask application instance.

    This function creates a Flask-RESTful Api instance, adds the resource
    endpoints for managing dummy items, and logs the successful registration
    of routes.
    """
    api = Api(app)

    api.add_resource(DummyListResource, '/dummies')
    api.add_resource(DummyResource, '/dummies/<int:dummy_id>')
    api.add_resource(ExportCSVResource, '/export/csv')
    api.add_resource(ImportCSVResource, '/import/csv')
    api.add_resource(ImportJSONResource, '/import/json')

    api.add_resource(VersionResource, '/version')
    api.add_resource(ConfigResource, '/config')
    api.add_resource(CompanyListResource, '/companies')
    api.add_resource(CompanyResource, '/companies/<string:company_id>')
    api.add_resource(CustomerListResource, '/customers')
    api.add_resource(CustomerResource, '/customers/<string:customer_id>')
    api.add_resource(OrganizationUnitListResource, '/organization_units')
    api.add_resource(OrganizationUnitResource, '/organization_units/<string:unit_id>')
    api.add_resource(OrganizationUnitChildrenResource, '/organization_units/<string:unit_id>/children')
    api.add_resource(PositionListResource, '/positions')
    api.add_resource(PositionResource, '/positions/<string:position_id>')
    api.add_resource(OrganizationUnitPositionsResource, '/organization_units/<string:unit_id>/positions')
    api.add_resource(SubcontractorListResource, '/subcontractors')
    api.add_resource(SubcontractorResource, '/subcontractors/<string:subcontractor_id>')
    api.add_resource(UserListResource, '/users')
    api.add_resource(UserResource, '/users/<string:user_id>')
    api.add_resource(UserCompanyResource, '/company/<string:company_id>/users')
    api.add_resource(UserPositionResource, '/position/<string:position_id>/users')
    api.add_resource(VerifyPasswordResource, '/verify_password')

    logger.info("Routes registered successfully.")
