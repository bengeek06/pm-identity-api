"""
health.py
---------
Health check resource for the Flask application.
This module provides a simple health check endpoint to verify that the service is running.
"""
from flask_restful import Resource
from app.logger import logger


class HealthResource(Resource):
    """
    Resource for health check endpoint.
    
    This resource provides a simple way to check if the service is running
    and responding to requests.
    """
    
    def get(self):
        """
        GET /health
        
        Returns:
            dict: A simple response indicating the service is healthy
            
        Returns:
            - 200: Service is healthy and running
        """
        logger.debug("Health check requested")
        
        return {
            "status": "healthy",
            "service": "auth_service",
            "message": "Service is running"
        }, 200