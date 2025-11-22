# Identity Service API

[![Tests](https://github.com/bengeek06/pm-identity-api/actions/workflows/python-app.yml/badge.svg?branch=guardian_staging)](https://github.com/bengeek06/pm-identity-api/actions)
[![License: AGPL v3 / Commercial](https://img.shields.io/badge/license-AGPLv3%20%2F%20Commercial-blue)](LICENSE.md)
[![OpenAPI Spec](https://img.shields.io/badge/OpenAPI-3.0.3-blue.svg)](openapi.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Flask](https://img.shields.io/badge/flask-%3E=2.0-green.svg)
![Coverage](https://img.shields.io/badge/tests-376%20tests-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

A production-ready API for managing users, companies, organizations, positions, subcontractors, and customers.  
This repository provides a solid foundation for your next identity or directory service, with environment-based configuration, Docker support, migrations, and a full OpenAPI 3.0 specification.

---

## Overview

The **Identity Service API** is a comprehensive, production-ready microservice for managing organizational identities and structures. Built with Flask and Flask-RESTful, it provides secure multi-tenant capabilities with JWT authentication and role-based access control.

**Key Capabilities:**
- **🏢 Company Management**: Multi-tenant architecture with company-based data isolation
- **👥 User Management**: Full user lifecycle with authentication and profile management  
- **🏗️ Organizational Structure**: Hierarchical organization units and position management
- **🤝 Business Relationships**: Customer and subcontractor management
- **🔐 Security & RBAC**: JWT cookie authentication with external Guardian service integration
- **📊 Health Monitoring**: Comprehensive health checks and monitoring endpoints
- **🔄 Database Management**: Automated migrations and initialization workflows

**Technical Stack:**
- **Backend**: Flask 2.0+ with Flask-RESTful for API endpoints
- **Database**: SQLAlchemy ORM with PostgreSQL/SQLite support
- **Authentication**: JWT tokens with HTTP-only cookie storage
- **Authorization**: External Guardian service for role-based permissions
- **Validation**: Marshmallow schemas for request/response validation
- **Testing**: pytest with comprehensive test coverage (376 tests)
- **Documentation**: OpenAPI 3.0.3 specification
---

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── email_helper.py
│   ├── logger.py
│   ├── rate_limiter.py
│   ├── routes.py
│   ├── storage_helper.py
│   ├── utils.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── company.py
│   │   ├── customer.py
│   │   ├── organization_unit.py
│   │   ├── password_reset_otp.py
│   │   ├── position.py
│   │   ├── subcontractor.py
│   │   └── user.py
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── company.py
│   │   ├── company_logo.py
│   │   ├── config.py
│   │   ├── customer.py
│   │   ├── health.py
│   │   ├── init_db.py
│   │   ├── organization_unit.py
│   │   ├── password_reset.py
│   │   ├── position.py
│   │   ├── subcontractor.py
│   │   ├── user.py
│   │   ├── user_auth.py
│   │   ├── user_avatar.py
│   │   ├── user_password.py
│   │   ├── user_permissions.py
│   │   ├── user_policies.py
│   │   ├── user_position.py
│   │   ├── user_roles.py
│   │   └── version.py
│   └── schemas/
│       ├── __init__.py
│       ├── company_schema.py
│       ├── customer_schema.py
│       ├── organization_unit_schema.py
│       ├── position_schema.py
│       ├── subcontractor_schema.py
│       └── user_schema.py
├── docs/
│   └── TESTING_STRATEGY.md
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│       └── 9d10e1359386_init.py
├── scripts/
│   ├── integration.conf.example
│   └── run-integration-tests.sh
├── tests/
│   ├── __init__.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── init_guardian.py
│   │   ├── test_company_logo_integration.py
│   │   ├── test_guardian_integration.py
│   │   └── test_user_avatar_integration.py
│   └── unit/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_company.py
│       ├── test_company_logo.py
│       ├── test_config.py
│       ├── test_customer.py
│       ├── test_guardian_disabled.py
│       ├── test_guardian_formats.py
│       ├── test_health.py
│       ├── test_init_api.py
│       ├── test_init_db.py
│       ├── test_jwt_forwarding.py
│       ├── test_organization_unit.py
│       ├── test_password_reset.py
│       ├── test_position.py
│       ├── test_run.py
│       ├── test_simple_guardian.py
│       ├── test_storage_helper.py
│       ├── test_subcontractor.py
│       ├── test_user.py
│       ├── test_user_avatar.py
│       ├── test_utils.py
│       ├── test_version.py
│       └── test_wsgi.py
├── CODE_OF_CONDUCT.md
├── COMMERCIAL-LICENSE.txt
├── CONTRIBUTING.md
├── docker-compose.test.yml
├── docker-entrypoint.sh
├── Dockerfile
├── env.example
├── LICENSE
├── LICENSE.md
├── openapi.yml
├── pytest.ini
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── run.py
├── sonar-project.properties
├── VERSION
├── wait-for-it.sh
└── wsgi.py
```

---

## Environments

The application supports multiple environments, each with its own configuration:

- **Development**: For local development. Debug mode enabled.
- **Testing**: For running automated tests. Uses a separate test database.
- **Staging**: For pre-production validation. Debug mode enabled, but production-like settings.
- **Production**: For live deployments. Debug mode disabled, secure settings.

Set the environment with the `FLASK_ENV` environment variable (`development`, `testing`, `staging`, `production`).  
Database URL and secrets are configured via environment variables (see `env.example`).

## Environment Variables

The service reads the following variables (see env.example):

| Variable                  | Description |
|---------------------------|-------------|
| FLASK_ENV                 | Environment (development, testing, staging, production) |
| LOG_LEVEL                 | Logging level (DEBUG, INFO, etc.) |
| DATABASE_URL              | SQLAlchemy database URL |
| GUARDIAN_SERVICE_URL      | External guardian service base URL (for RBAC verification) |
| GUARDIAN_SERVICE_TIMEOUT  | Timeout in seconds for Guardian service API calls (default: 5) |
| JWT_SECRET                | Secret used to sign JWTs |
| INTERNAL_AUTH_TOKEN       | Shared secret with auth service |
| STORAGE_SERVICE_URL       | Storage service base URL for avatar management (default: http://storage-service:5000) |
| STORAGE_REQUEST_TIMEOUT   | Timeout in seconds for Storage service API calls (default: 30) |
| MAX_AVATAR_SIZE_MB        | Maximum avatar file size in MB (default: 5) |
| USE_STORAGE_SERVICE       | Enable/disable Storage Service integration (true/false, default: true) |

---

## Features

- **Environment-based configuration**: Easily switch between development, testing, staging, and production using the `FLASK_ENV` environment variable.
- **RESTful API**: CRUD endpoints for users, companies, organizations, positions, subcontractors, and customers.
- **JWT Cookie Authentication**: Secure authentication using HTTP-only cookies with company isolation.
- **Role-Based Access Control (RBAC)**: Integration with Guardian service for fine-grained permission management.
- **Multi-tenant Architecture**: Company-based data isolation ensuring users can only access their organization's data.
- **OpenAPI 3.0 documentation**: See [`openapi.yml`](openapi.yml).
- **Docker-ready**: Includes a `Dockerfile` and healthcheck script.
- **Database migrations**: Managed with Alembic/Flask-Migrate.
- **Testing**: Pytest-based test suite with 59+ comprehensive tests.
- **Logging**: Colored logging for better readability.

### 🔐 **Authentication & Authorization**

The API uses **JWT token authentication** stored in HTTP-only cookies for enhanced security:

- **JWT Tokens**: Contain `user_id` and `company_id` for multi-tenant isolation
- **Cookie-based**: Tokens are stored in secure HTTP-only cookies (`access_token`)
- **Guardian Integration**: External RBAC service for permission verification
- **Company Isolation**: All operations are automatically scoped to the authenticated user's company
- **Permission Checks**: Each endpoint verifies permissions through Guardian service before allowing access

**Authentication Flow:**
1. User authenticates and receives JWT cookie
2. Each request includes the JWT cookie automatically
3. Service validates JWT and extracts `user_id` + `company_id`  
4. Permission check sent to Guardian service with forwarded JWT
5. Data operations filtered by company for multi-tenant isolation

---

## Quickstart
### Requirements

- Python 3.11+
- pip

### Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

(For development tooling:)

```bash
pip install -r requirements-dev.txt
```

### Environment

Copy and edit the example environment file:

```bash
cp env.example .env.development # or .env.test
```

Set at least:

- `FLASK_ENV=development`
- `DATABASE_URL=sqlite:///dev.db`
- `GUARDIAN_SERVICE_URL=http://guardian_service:5000`
- `JWT_SECRET=your_jwt_secret`
- `INTERNAL_AUTH_TOKEN=your_internal_secret`

### Running

```bash
flask -e .env.development db upgrade
flask -e .env.development run
```
or
```bash
python run.py
```
Gunicorn (production-style):

```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

---

## API Documentation

The OpenAPI specification is available in [openapi.yml](openapi.yml).  
You can visualize it with [Swagger Editor](https://editor.swagger.io/) or [Redoc](https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/bengeek06/pm-identity-api/refs/heads/guardian_staging/openapi.yml).


---

## Endpoints

### 🔧 **System Endpoints**
| Method | Path        | Description                                  | Auth Required |
|--------|-------------|----------------------------------------------|---------------|
| GET    | `/health`   | Health check endpoint with database status   | ❌            |
| GET    | `/version`  | Get API version information                  | ✅            |
| GET    | `/config`   | Get application configuration                | ❌            |
| GET    | `/init-db`  | Check database initialization status         | ❌            |
| POST   | `/init-db`  | Initialize database with admin user & company| ❌            |

### 🔧 **Users Endpoints**
| Method | Path                             | Description                                 | Auth Required |
|--------|----------------------------------|---------------------------------------------|---------------|
| GET    | /users                           | List users from authenticated company       |✅            |
| POST   | /users                           | Create a new user                           |✅            |
| GET    | /users/{user_id}                 | Get user by ID                              |✅            |
| PUT    | /users/{user_id}                 | Update user by ID                           |✅            |
| PATCH  | /users/{user_id}                 | Partially update user by ID                 |✅            |
| DELETE | /users/{user_id}                 | Delete user by ID                           |✅            |
| POST   | /verify_password                 | Verify a user's password by email           |❌            |
| GET    | /users/{user_id}/roles           | Get roles assigned to a user                |✅            |
| POST   | /users/{user_id}/roles           | Assign a role to a user                     |✅            |
| GET    | /users/{user_id}/roles/{role_id} | Get specific role assignment for a user     |✅            |
| DELETE | /users/{user_id}/roles/{role_id} | Remove specific role from a user            |✅            |
| GET    | /positions/{position_id}/users   | Get users assigned to a specific position   |✅            |
| POST   | /users/{user_id}/avatar          | Upload user avatar image                    |✅            |
| GET    | /users/{user_id}/avatar          | Download user avatar image                  |✅            |
| DELETE | /users/{user_id}/avatar          | Delete user avatar image                    |✅            |
| POST   | /users/{user_id}/admin-reset-password | Admin-initiated password reset         |✅            |
| PATCH  | /users/me/change-password        | User changes own password                   |✅            |
| POST   | /users/password-reset/request    | Request password reset OTP via email        |✅            |
| POST   | /users/password-reset/confirm    | Confirm password reset with OTP             |✅            |

#### 📷 **User Avatar Management**

User avatars are managed through the Storage Service integration. The workflow is designed to avoid 404 errors on the frontend:

**Upload Avatar:**
```bash
POST /users/{user_id}/avatar
Content-Type: multipart/form-data

# Form data:
avatar: [image file - JPG, PNG, GIF, BMP, WEBP]
```
- Maximum file size: 5 MB (configurable via `MAX_AVATAR_SIZE_MB`)
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`
- Access control: Only the user themselves can upload their avatar
- Response includes `file_id` for tracking

**Download Avatar (Frontend Integration):**
```bash
GET /users/{user_id}/avatar
```

**⚠️ Important for Frontend**: Before attempting to download an avatar, **check the `has_avatar` field** from the user object:
```json
GET /users/{user_id}
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "has_avatar": true,  // ← Check this before downloading
  ...
}
```

**Recommended Frontend Pattern:**
```javascript
// 1. Fetch user data
const user = await fetch('/users/{user_id}').then(r => r.json());

// 2. Only download avatar if has_avatar is true
if (user.has_avatar) {
  const avatarUrl = '/users/{user_id}/avatar';
  // Display avatar
} else {
  // Show default avatar placeholder
}
```

This approach prevents unnecessary 404 requests when users don't have avatars uploaded.

**Delete Avatar:**
```bash
DELETE /users/{user_id}/avatar
```
- Access control: Only the user themselves can delete their avatar
- After deletion, `has_avatar` will be set to `false`

**Storage Service Configuration:**
- Avatars are stored with normalized `.png` extensions (browser reads `Content-Type` header, not extension)
- Set `USE_STORAGE_SERVICE=false` to disable avatar features (for testing/development)
- When disabled, all avatar endpoints return 503 Service Unavailable

#### 🔑 **Password Management**

The Identity Service provides secure password management with admin reset and user self-service capabilities.

**Admin Password Reset (Phase 1):**
```bash
POST /users/{user_id}/admin-reset-password
```
- Generates a secure 12-character temporary password
- Marks user as requiring password change on next login
- Enforces multi-tenant isolation (admin and user must be in same company)
- Requires Guardian 'update' permission on 'admin_password_reset' resource
- Temporary password shown only once in response

**Response Example:**
```json
{
  "message": "Password reset successful",
  "temporary_password": "aB3$xY9#kL2m",
  "password_reset_required": true,
  "note": "User must change password on next login. This is the only time the temporary password will be shown."
}
```

**User Password Change:**
```bash
PATCH /users/me/change-password
Content-Type: application/json

{
  "current_password": "OldPassword123",
  "new_password": "NewSecurePassword456"
}
```
- Requires current password verification
- New password must be at least 8 characters
- Clears `password_reset_required` flag automatically
- Updates `last_password_change` timestamp
- User can only change their own password

**Password Reset Flow:**
1. Admin calls `/users/{user_id}/admin-reset-password`
2. System generates temporary password and sets `password_reset_required = true`
3. Admin communicates temporary password to user (out of band)
4. User logs in with temporary password
5. User calls `/users/me/change-password` to set new password
6. System clears `password_reset_required` flag

**Security Features:**
- Temporary passwords use cryptographically secure random generation (`secrets` module)
- Passwords are hashed using werkzeug's secure password hashing (PBKDF2)
- Multi-tenant isolation prevents cross-company password resets
- All password operations are logged for audit trails
- Timezone-aware timestamps (Python 3.12+ compatible)

**Email-Based Password Reset (Phase 2):**

Self-service password reset with OTP codes sent via email.

**Request Password Reset:**
```bash
POST /users/password-reset/request
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response (Always 200 OK):**
```json
{
  "message": "If an account with this email exists, a password reset code has been sent."
}
```

**Security Features:**
- **Rate Limiting**: 50 requests/hour, 200/day per IP address
- **Email Enumeration Protection**: Always returns 200 OK, never reveals if email exists
- **OTP Expiration**: 15 minutes (configurable via `PASSWORD_RESET_OTP_TTL_MINUTES`)
- **Attempt Limiting**: Maximum 3 verification attempts per OTP
- **Automatic Invalidation**: Previous OTPs invalidated on new request
- **IP Logging**: All requests logged with IP address for security monitoring

**Confirm Password Reset:**
```bash
POST /users/password-reset/confirm
Content-Type: application/json

{
  "email": "user@example.com",
  "otp_code": "123456",
  "new_password": "NewSecurePassword456"
}
```

**Success Response (200 OK):**
```json
{
  "message": "Password reset successful"
}
```

**Error Response (400 Bad Request):**
```json
{
  "message": "Invalid or expired OTP code"
}
```

**Email Service Configuration:**

To enable email-based password reset, configure these environment variables:

```bash
# Enable/disable email service
USE_EMAIL_SERVICE=true

# SMTP Configuration
MAIL_SERVER=smtp.gmail.com          # Your SMTP server
MAIL_PORT=587                        # SMTP port (587 for TLS, 465 for SSL)
MAIL_USE_TLS=true                    # Use TLS encryption
MAIL_USE_SSL=false                   # Use SSL encryption (mutually exclusive with TLS)
MAIL_USERNAME=noreply@example.com    # SMTP username
MAIL_PASSWORD=your-app-password      # SMTP password or app-specific password
MAIL_DEFAULT_SENDER=noreply@waterfall-identity.com  # Default sender address
MAIL_MAX_EMAILS=100                  # Max emails per connection (optional)

# Rate Limiting Configuration
RATELIMIT_STORAGE_URI=memory://      # Storage backend (memory:// or redis://url)
RATELIMIT_STRATEGY=fixed-window      # Rate limit strategy

# OTP Configuration
PASSWORD_RESET_OTP_TTL_MINUTES=15    # OTP expiration time (default: 15 minutes)
PASSWORD_RESET_OTP_MAX_ATTEMPTS=3    # Max verification attempts (default: 3)
```

**Gmail Example Configuration:**
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password  # Create at https://myaccount.google.com/apppasswords
```

**Email Template:**

The password reset email includes:
- Professional HTML formatting with CSS styling
- Plain text fallback for email clients that don't support HTML
- User's first name personalization
- 6-digit OTP code prominently displayed
- 15-minute expiration notice
- Security warning about not sharing the code

**Password Reset Flow (Phase 2):**
1. User requests password reset at `/users/password-reset/request`
2. System checks if email exists (never revealed in response)
3. If user exists:
   - Generate 6-digit OTP code
   - Hash and store OTP with 15-minute expiration
   - Send OTP via email to user
   - Invalidate any previous OTPs
4. Always return generic success message (prevents email enumeration)
5. User receives email with OTP code
6. User submits OTP and new password at `/users/password-reset/confirm`
7. System validates:
   - OTP exists and matches hash
   - OTP not expired (< 15 minutes old)
   - OTP not already used
   - Attempts < 3
   - New password >= 8 characters
8. If valid:
   - Update password
   - Mark OTP as used
   - Clear `password_reset_required` flag
   - Update `last_password_change` timestamp

**Database Schema:**

Phase 2 adds the `password_reset_otp` table:
```sql
CREATE TABLE password_reset_otp (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES user(id) ON DELETE CASCADE,
    otp_code VARCHAR(255) NOT NULL,  -- Hashed with werkzeug
    attempts INTEGER DEFAULT 0,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    used_at DATETIME NULL
);
```

**Testing Without Email Service:**

When `USE_EMAIL_SERVICE=false`:
- Password reset endpoints still work
- OTP generation and validation work normally
- Emails are not sent (logged instead)
- Useful for development and testing

### 🎭 **User Roles Management**

The Identity Service integrates with the Guardian service for comprehensive role-based access control:

**Role Assignment Flow:**
- **GET** `/users/{user_id}/roles` - Retrieve all roles assigned to a user
- **POST** `/users/{user_id}/roles` - Assign a new role (requires `role_id` in JSON body)
- **GET** `/users/{user_id}/roles/{role_id}` - Get details of a specific role assignment
- **DELETE** `/users/{user_id}/roles/{role_id}` - Remove a specific role from the user

**Guardian Service Integration:**
- All role operations are forwarded to the external Guardian service
- JWT cookies are automatically forwarded for authentication context
- Supports multiple Guardian response formats for flexibility
- Cross-company role assignments are prevented through company validation


### 🔧 **Companies Endpoints**
| Method | Path                    | Description                                  | Auth Required |
|--------|-------------------------|----------------------------------------------|---------------|
| GET    | /companies              | List companies                               |✅            |
| POST   | /companies              | Create a new company                         |✅            |
| GET    | /companies/{company_id} | Get company by ID                            |✅            |
| PUT    | /companies/{company_id} | Update company by ID                         |✅            |
| PATCH  | /companies/{company_id} | Partially update company by ID               |✅            |
| DELETE | /companies/{company_id} | Delete company by ID                         |✅            |

### 🔧 **Organization Units Endpoints**
| Method | Path                                     | Description                                  | Auth Required |
|--------|------------------------------------------|----------------------------------------------|---------------|
| GET    | /organization_units                      | List organization units                      |✅            |
| POST   | /organization_units                      | Create an organization unit                  |✅            |
| GET    | /organization_units/{unit_id}            | Get organization unit by ID                  |✅            |
| PUT    | /organization_units/{unit_id}            | Update organization unit by ID               |✅            |
| PATCH  | /organization_units/{unit_id}            | Partially update organization unit by ID     |✅            |
| DELETE | /organization_units/{unit_id}            | Delete organization unit by ID               |✅            |
| GET    | /organization_units/{unit_id}/children   | Get child units of an organization unit      |✅            |
| GET    | /organization_units/{unit_id}/positions  | Get positions within an organization unit    |✅            |

### 🔧 **Positions Endpoints**
| Method | Path        | Description                                  | Auth Required |
|--------|-------------|----------------------------------------------|---------------|
| POST   | /positions                             | Create a new position                       |✅            |
| GET    | /positions                             | List positions                              |✅            |
| GET    | /positions/{position_id}               | Get position by ID                          |✅            |
| PUT    | /positions/{position_id}               | Update position by ID                       |✅            |
| PATCH  | /positions/{position_id}               | Partially update position by ID             |✅            |
| DELETE | /positions/{position_id}               | Delete position by ID                       |✅            |

### 🔧 **Customers Endpoints**
| Method | Path        | Description                                  | Auth Required |
|--------|-------------|----------------------------------------------|---------------|
| POST   | /customers                             | Create a new customer                       |✅            |
| GET    | /customers                             | List customers                              |✅            |
| GET    | /customers/{customer_id}               | Get customer by ID                          |✅            |
| PUT    | /customers/{customer_id}               | Update customer by ID                       |✅            |
| PATCH  | /customers/{customer_id}               | Partially update customer by ID             |✅            |
| DELETE | /customers/{customer_id}               | Delete customer by ID                       |✅            |

### 🔧 **Subcontractors Endpoints**
| Method | Path        | Description                                  | Auth Required |
|--------|-------------|----------------------------------------------|---------------|
| POST   | /subcontractors                        | Create a new subcontractor                  |✅            |
| GET    | /subcontractors                        | List subcontractors                         |✅            |
| GET    | /subcontractors/{subcontractor_id}     | Get subcontractor by ID                     |✅            |
| PUT    | /subcontractors/{subcontractor_id}     | Update subcontractor by ID                  |✅            |
| PATCH  | /subcontractors/{subcontractor_id}     | Partially update subcontractor by ID        |✅            |
| DELETE | /subcontractors/{subcontractor_id}     | Delete subcontractor by ID                  |✅            |

### 📝 **Authentication Notes**

**JWT Authentication**: All protected endpoints (✅) require a valid JWT token containing:
- `user_id`: User identifier for access control context
- `company_id`: Company/tenant identifier for multi-tenant isolation

**Request Format**: JWT tokens are passed via HTTP-only cookies (`access_token`) for enhanced security.

**Guardian Integration**: Role-based permissions are verified through external Guardian service:
- Each protected endpoint forwards JWT cookies to Guardian for permission verification
- Guardian service returns role assignments and permission decisions
- Supports flexible response formats from Guardian service

**Multi-tenant Isolation**: All data operations are automatically filtered by `company_id`:
- Users can only access data from their own company
- Cross-company access is prevented at the database level
- Company context is extracted from authenticated JWT token

**Public Endpoints**: `/health`, `/init-db`, and `/verify_password` do not require authentication.

**Error Responses**: 
- `401 Unauthorized`: Missing, invalid, or expired JWT token
- `403 Forbidden`: Valid authentication but insufficient permissions via Guardian
- `400 Bad Request`: Invalid request data or malformed UUIDs
- `404 Not Found`: Resource not found within company context
- `409 Conflict`: Resource already exists or constraint violation
- `500 Internal Server Error`: Guardian service unavailable or database errors

---


## Running Tests

```bash
pytest
```

(Uses FLASK_ENV=testing automatically via conftest.)

---

## Docker Usage

You can run the service using the production image (either locally built or from GHCR).

### Run with docker (production mode)

```bash
docker run -d \
  --name identity_service \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e LOG_LEVEL=INFO \
  -e DATABASE_URL=postgresql://user:pass@db:5432/identity_prod \
  -e GUARDIAN_SERVICE_URL=http://guardian_service:5000 \
  -e INTERNAL_AUTH_TOKEN=change-me-internal \
  -e JWT_SECRET=change-me-jwt \
  ghcr.io/<owner>/<repo>:latest
```

If you built locally:
```bash
docker build -t identity-service:prod --target production .
docker run -d --name identity_service -p 5000:5000 -e FLASK_ENV=production identity-service:prod
```

Optional (supported by entrypoint if present):
- `WAIT_FOR_DB=true`
- `RUN_MIGRATIONS=true`

### docker-compose example

```yaml
version: "3.9"

services:
  identity_service:
    image: ghcr.io/<owner>/<repo>:latest
    container_name: identity_service
    restart: unless-stopped
    environment:
      FLASK_ENV: production
      LOG_LEVEL: INFO
      DATABASE_URL: postgresql://identity_user:identity_pass@db:5432/identity_db
      GUARDIAN_SERVICE_URL: http://guardian_service:5000
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN:-change-me-internal}
      JWT_SECRET: ${JWT_SECRET:-change-me-jwt}
      WAIT_FOR_DB: "true"
      RUN_MIGRATIONS: "true"
    depends_on:
      - db
    ports:
      - "5000:5000"

  db:
    image: postgres:15-alpine
    container_name: identity_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: identity_user
      POSTGRES_PASSWORD: identity_pass
      POSTGRES_DB: identity_db
    volumes:
      - identity_pg_data:/var/lib/postgresql/data

  # Example identity service dependency
  guardian_service:
    image: ghcr.io/<owner>/<guardian-service-repo>:latest
    environment:
      FLASK_ENV: production
    restart: unless-stopped

volumes:
  identity_pg_data:
```

Create a `.env` file alongside docker-compose to override secrets:

```
INTERNAL_AUTH_TOKEN=super-secret-internal
JWT_SECRET=super-secret-jwt
```

Start:
```bash
docker compose up -d
```
### Health check

```bash
curl -s http://localhost:5000/health
```

---

## License

This project is dual-licensed:

- **Community version**: [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html)
- **Commercial license**: See [LICENSE.md](LICENSE.md) and [COMMERCIAL-LICENCE.txt](COMMERCIAL-LICENCE.txt) for commercial licensing options

For commercial use or support, contact: **bengeek06@gmail.com**

---

## Contributing

We welcome contributions! Please read our contribution guidelines:

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development workflow, coding standards, and pull request process
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** - Community guidelines and expectations

For the overall Waterfall project workflow and branch strategy, see the [main CONTRIBUTING.md](https://github.com/bengeek06/waterfall/blob/main/CONTRIBUTING.md) at the repository root.

---
