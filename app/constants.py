"""
module: app.constants

Centralized constants for the Identity Service API.
Defines reusable message strings for logs, errors, and responses.
"""

# ============================================================================
# Log Messages
# ============================================================================
LOG_VALIDATION_ERROR = "Validation error: %s"
LOG_INTEGRITY_ERROR = "Integrity error: %s"
LOG_DATABASE_ERROR = "Database error: %s"

# ============================================================================
# HTTP Response Messages
# ============================================================================
MSG_VALIDATION_ERROR = "Validation error"
MSG_INTEGRITY_ERROR = "Integrity error"
MSG_INTEGRITY_ERROR_DUPLICATE = "Integrity error, possibly duplicate entry."
MSG_DATABASE_ERROR = "Database error"
MSG_DATABASE_ERROR_OCCURRED = "Database error occurred."
MSG_NOT_FOUND = "%s not found"
MSG_DELETED_SUCCESSFULLY = "%s deleted successfully"

# ============================================================================
# Entity-specific Messages
# ============================================================================
# User
MSG_USER_NOT_FOUND = "User not found"
MSG_USER_DELETED = "User deleted successfully"

# Company
MSG_COMPANY_NOT_FOUND = "Company not found"
MSG_COMPANY_DELETED = "Company deleted successfully"

# Position
MSG_POSITION_NOT_FOUND = "Position not found"
MSG_POSITION_DELETED = "Position deleted successfully"

# Organization Unit
MSG_ORG_UNIT_NOT_FOUND = "Organization unit not found"
MSG_ORG_UNIT_DELETED = "Organization unit deleted successfully"

# Customer
MSG_CUSTOMER_NOT_FOUND = "Customer not found"
MSG_CUSTOMER_DELETED = "Customer deleted successfully"

# Subcontractor
MSG_SUBCONTRACTOR_NOT_FOUND = "Subcontractor not found"
MSG_SUBCONTRACTOR_DELETED = "Subcontractor deleted successfully"
