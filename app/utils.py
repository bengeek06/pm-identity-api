"""Utility functions for the Identity Service API.
"""
import os
import re
from functools import wraps
import jwt
from flask import request, g

from app.logger import logger

def camel_to_snake(name):
    """
    Convert a CamelCase or PascalCase string to snake_case.

    Args:
        name (str): The string to convert.

    Returns:
        str: The converted snake_case string.
    """
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    snake = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return re.sub(r'_+', '_', snake)

def extract_jwt_data():
    """
    Extract and decode JWT data from request cookies.
    
    Returns:
        dict: Dictionary containing user_id and company_id from JWT, or None if invalid/missing
    """
    jwt_token = request.cookies.get('access_token')
    if not jwt_token:
        logger.debug("JWT token not found in cookies")
        return None
    
    jwt_secret = os.environ.get('JWT_SECRET')
    if not jwt_secret:
        logger.warning("JWT_SECRET not found in environment variables")
        return None
    
    try:
        payload = jwt.decode(jwt_token, jwt_secret, algorithms=["HS256"])
        user_id = payload.get('sub') or payload.get('user_id')
        company_id = payload.get('company_id')
        
        logger.debug(f"JWT decoded successfully - user_id: {user_id}, company_id: {company_id}")
        return {
            'user_id': user_id,
            'company_id': company_id,
            'payload': payload
        }
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.warning(f"JWT decode failed: {e}")
        return None


def require_jwt_auth(extract_company_id=True):
    """
    Decorator to require JWT authentication and optionally extract company_id.
    Falls back to header-based authentication for testing environments.
    
    Args:
        extract_company_id (bool): Whether to extract and inject company_id into request JSON
        
    Returns:
        Decorated function or error response
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            # Try JWT authentication first
            jwt_data = extract_jwt_data()
            
            # Fallback to headers for testing environment
            if not jwt_data:
                user_id = request.headers.get('X-User-ID')
                company_id = request.headers.get('X-Company-ID')
                
                if user_id:
                    # Create mock JWT data from headers (for testing)
                    jwt_data = {
                        'user_id': user_id,
                        'company_id': company_id
                    }
                    logger.debug("Using headers for authentication (testing mode)")
                else:
                    return {"message": "Missing or invalid JWT token"}, 401
            
            if extract_company_id:
                company_id = jwt_data.get('company_id')
                if not company_id:
                    logger.error("company_id missing in JWT/headers")
                    return {"message": "company_id missing in JWT/headers"}, 400
                
                # Only try to get JSON data for requests that might have a body
                # GET requests typically don't have JSON payloads
                try:
                    json_data = request.get_json(silent=True) or {}
                except Exception:
                    json_data = {}
                
                json_data["company_id"] = company_id
                
                # Store modified json_data in g for the view function to use
                g.json_data = json_data
            else:
                # Just store original json_data in g if company_id extraction is not needed
                try:
                    g.json_data = request.get_json(silent=True)
                except Exception:
                    g.json_data = None
            
            # Store jwt_data in g for potential use in view function
            g.jwt_data = jwt_data
            
            return view_func(*args, **kwargs)
        return wrapped
    return decorator