# Contributing to Identity Service

Thank you for your interest in contributing to the **Identity Service**!

> **Note**: This service is part of the larger [Waterfall](https://github.com/bengeek06/waterfall/blob/main/README.md) project. For the overall development workflow, branch strategy, and contribution guidelines, please refer to the [main CONTRIBUTING.md](https://github.com/bengeek06/waterfall/blob/main/CONTRIBUTING.md) in the root repository.

## Table of Contents

- [Service Overview](#service-overview)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [API Development](#api-development)
- [Database Migrations](#database-migrations)
- [Common Tasks](#common-tasks)

## Service Overview

The **Identity Service** manages user identities, companies, organizational structures, and positions for the Waterfall platform:

- **Technology Stack**: Python 3.13+, Flask 3.1+, SQLAlchemy, PostgreSQL
- **Port**: 5002 (containerized) / 5000 (standalone)
- **Responsibilities**:
  - User management (CRUD operations)
  - Company and customer management
  - Organizational unit hierarchy
  - Position management
  - Subcontractor tracking
  - Password verification for Auth Service
  - User-role integration with Guardian Service

**Key Dependencies:**
- Flask 3.1+ for web framework
- Flask-RESTful for REST API resources
- SQLAlchemy for ORM
- Marshmallow for serialization/validation
- PostgreSQL for data persistence
- Gunicorn for production WSGI server

## Development Setup

### Prerequisites

- Python 3.13+
- PostgreSQL 16+ (or use Docker)
- pip and virtualenv

### Local Setup

```bash
# Navigate to service directory
cd services/identity_service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development tools
pip install -r requirements-dev.txt

# Copy environment configuration
cp env.example .env.development

# Configure environment variables
# Edit .env.development with your local settings
```

### Environment Configuration

Create `.env.development` with the following variables:

```bash
# Flask environment
FLASK_ENV=development
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://identity_user:identity_pass@localhost:5432/identity_dev

# External services
GUARDIAN_SERVICE_URL=http://localhost:5003
INTERNAL_AUTH_TOKEN=dev-internal-secret

# Security
JWT_SECRET=dev-jwt-secret-change-in-production
```

### Database Setup

```bash
# Create database (if using local PostgreSQL)
createdb identity_dev

# Run migrations
flask -e .env.development db upgrade

# Or use Docker for PostgreSQL
docker run -d \
  --name identity_db_dev \
  -e POSTGRES_USER=identity_user \
  -e POSTGRES_PASSWORD=identity_pass \
  -e POSTGRES_DB=identity_dev \
  -p 5432:5432 \
  postgres:16-alpine
```

### Running the Service

```bash
# Development mode with auto-reload
python run.py

# Or with Flask CLI
export FLASK_APP=wsgi:app
flask run --port=5000

# Production-style with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

The service will be available at `http://localhost:5000`

## Coding Standards

### Python Style Guide

This service follows **PEP 8** style guidelines with the following tools:

**Black** - Code formatter:
```bash
# Format all code
black -l 79 -t py313 app/ tests/

# Check without modifying
black -l 79 -t py313 --check app/ tests/
```

**Pylint** - Linter:
```bash
# Check code quality
pylint app/ tests/

# Configuration in .pylintrc or pyproject.toml
```

**isort** - Import sorting:
```bash
# Sort imports
isort app/ tests/

# Check only
isort --check-only app/ tests/
```

### Code Conventions

**Type Hints** (Python 3.13+):
```python
from typing import Optional, List, Dict, Any
from app.models import User, Company

def get_users_by_company(company_id: int, active_only: bool = True) -> List[User]:
    """Get all users belonging to a company.
    
    Args:
        company_id: The company's database ID
        active_only: If True, return only active users
    
    Returns:
        List of User objects
    
    Raises:
        ValueError: If company_id is invalid
    """
    # Implementation
    pass
```

**Docstrings** (Google style):
```python
class OrganizationUnit(db.Model):
    """Organizational unit model representing company hierarchy.
    
    Attributes:
        id: Primary key
        name: Unit name
        company_id: Foreign key to company
        parent_id: Self-referential FK for hierarchy
        level: Hierarchy level (0 = root)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    pass
```

**Resource/Endpoint Structure (Flask-RESTful):**

This service uses **Flask-RESTful** for API implementation. Resources are defined as classes in `app/resources/` and registered centrally in `app/routes.py`.

```python
# app/resources/company.py
from flask import request, g
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import db
from app.logger import logger
from app.models.company import Company
from app.schemas.company_schema import CompanySchema
from app.utils import require_jwt_auth, check_access_required


class CompanyListResource(Resource):
    """Resource for managing the collection of companies."""
    
    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """
        Retrieve all companies.
        
        Returns:
            tuple: List of serialized companies and HTTP status code 200.
        """
        logger.info("Retrieving all companies")
        
        try:
            companies = Company.get_all()
            company_schema = CompanySchema(session=db.session, many=True)
            return company_schema.dump(companies), 200
        except SQLAlchemyError as e:
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
    
    @require_jwt_auth()
    @check_access_required("create")
    def post(self):
        """
        Create a new company.
        
        Expects:
            JSON payload with required fields.
        
        Returns:
            tuple: Serialized created company and HTTP status code 201.
        """
        logger.info("Creating a new company")
        
        json_data = request.get_json()
        company_schema = CompanySchema(session=db.session)
        
        try:
            new_company = company_schema.load(json_data)
            db.session.add(new_company)
            db.session.commit()
            return company_schema.dump(new_company), 201
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"message": "Validation error", "errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400


class CompanyResource(Resource):
    """Resource for managing a single company."""
    
    @require_jwt_auth()
    @check_access_required("read")
    def get(self, company_id):
        """Retrieve a specific company by ID."""
        logger.info("Retrieving company with ID: %s", company_id)
        
        company = Company.get_by_id(company_id)
        if not company:
            logger.warning("Company with ID %s not found", company_id)
            return {"message": "Company not found"}, 404
        
        company_schema = CompanySchema(session=db.session)
        return company_schema.dump(company), 200
    
    @require_jwt_auth()
    @check_access_required("update")
    def put(self, company_id):
        """Update a company by ID (full update)."""
        # Implementation
        pass
    
    @require_jwt_auth()
    @check_access_required("update")
    def patch(self, company_id):
        """Partially update a company by ID."""
        # Implementation
        pass
    
    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, company_id):
        """Delete a company by ID."""
        # Implementation
        pass
```

**Route Registration** (centralized in `app/routes.py`):
```python
# app/routes.py
from flask_restful import Api
from app.resources.company import CompanyListResource, CompanyResource
from app.resources.user import UserListResource, UserResource

def register_routes(app):
    """Register all REST API routes on the Flask application."""
    api = Api(app)
    
    # Company endpoints
    api.add_resource(CompanyListResource, "/companies")
    api.add_resource(CompanyResource, "/companies/<string:company_id>")
    
    # User endpoints
    api.add_resource(UserListResource, "/users")
    api.add_resource(UserResource, "/users/<string:user_id>")
    
    # ... other resources
    
    logger.info("Routes registered successfully.")
```

**Key Patterns:**
- **One Resource Class per HTTP Method Group**: `ListResource` for collections (GET, POST), `Resource` for single items (GET, PUT, PATCH, DELETE)
- **Authentication Decorators**: `@require_jwt_auth()` for JWT validation, `@check_access_required()` for RBAC
- **Marshmallow Schemas**: All validation and serialization via schemas
- **Error Handling**: Consistent try/except blocks with specific SQLAlchemy exceptions
- **Logging**: Structured logging with context (user_id, company_id, etc.)
- **Multi-tenancy**: Company_id injection from JWT token via `g.company_id`

### Marshmallow Schemas

```python
# app/schemas/user_schema.py
from marshmallow import Schema, fields, validate, validates, ValidationError

class UserSchema(Schema):
    """Schema for User serialization and validation."""
    
    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    company_id = fields.Int(required=True)
    position_id = fields.Int(allow_none=True)
    is_active = fields.Bool(missing=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested relationships
    company = fields.Nested('CompanySchema', dump_only=True)
    position = fields.Nested('PositionSchema', dump_only=True)
    
    @validates('email')
    def validate_email_unique(self, value):
        """Ensure email is unique."""
        if User.query.filter_by(email=value).first():
            raise ValidationError("Email already exists")
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_users.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test class or method
pytest tests/test_users.py::TestUserEndpoints::test_create_user
```

### Test Structure

```python
import pytest
from app import create_app
from app.models import db, User, Company

class TestUserEndpoints:
    """Test suite for user management endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self, client):
        """Setup test data for each test."""
        # Create test company
        company = Company(name="Test Company")
        db.session.add(company)
        db.session.commit()
        self.company_id = company.id
        
        yield
        
        # Cleanup
        db.session.query(User).delete()
        db.session.query(Company).delete()
        db.session.commit()
    
    def test_create_user(self, client):
        """Test creating a new user."""
        response = client.post('/users', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'company_id': self.company_id,
            'password': 'SecurePass123!'
        })
        
        assert response.status_code == 201
        data = response.json
        assert data['email'] == 'test@example.com'
        assert 'id' in data
    
    def test_get_users_by_company(self, client):
        """Test filtering users by company."""
        # Create test users
        user = User(
            email='user@test.com',
            username='user1',
            company_id=self.company_id
        )
        db.session.add(user)
        db.session.commit()
        
        response = client.get(f'/users?company_id={self.company_id}')
        
        assert response.status_code == 200
        data = response.json
        assert len(data) == 1
        assert data[0]['company_id'] == self.company_id
```

### Test Coverage Requirements

- **Minimum coverage**: 80% for new code
- **Critical paths**: User creation, company management, org hierarchy require 100% coverage
- **Focus areas**: Data validation, relationship integrity, error handling

## API Development

### Adding a New Resource

1. **Create model** in `app/models/`:

```python
# app/models/my_model.py
from app.models import db
from datetime import datetime

class MyModel(db.Model):
    """Model description."""
    
    __tablename__ = 'my_table'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='my_models')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat()
        }
```

2. **Create schema** in `app/schemas/`:

```python
# app/schemas/my_schema.py
from marshmallow import Schema, fields

class MyModelSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    company_id = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)
    
    company = fields.Nested('CompanySchema', dump_only=True)
```

3. **Create resource** in `app/resources/`:

```python
# app/resources/my_resource.py
from flask import request, g
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import db
from app.logger import logger
from app.models.my_model import MyModel
from app.schemas.my_schema import MyModelSchema
from app.utils import require_jwt_auth, check_access_required


class MyModelListResource(Resource):
    """Resource for managing the collection of MyModel entities."""
    
    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """
        Retrieve all MyModel items.
        
        Returns:
            tuple: List of serialized items and HTTP status code 200.
        """
        logger.info("Retrieving all MyModel items")
        
        try:
            items = MyModel.get_all()
            schema = MyModelSchema(session=db.session, many=True)
            return schema.dump(items), 200
        except SQLAlchemyError as e:
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
    
    @require_jwt_auth()
    @check_access_required("create")
    def post(self):
        """
        Create a new MyModel item.
        
        Expects:
            JSON payload with required fields.
        
        Returns:
            tuple: Serialized created item and HTTP status code 201.
        """
        logger.info("Creating a new MyModel item")
        
        json_data = request.get_json()
        schema = MyModelSchema(session=db.session)
        
        # Inject company_id from JWT if required
        json_data["company_id"] = g.company_id
        
        try:
            new_item = schema.load(json_data)
            db.session.add(new_item)
            db.session.commit()
            return schema.dump(new_item), 201
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"message": "Validation error", "errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500


class MyModelResource(Resource):
    """Resource for managing a single MyModel entity."""
    
    @require_jwt_auth()
    @check_access_required("read")
    def get(self, my_model_id):
        """Retrieve a specific MyModel item by ID."""
        logger.info("Retrieving MyModel with ID: %s", my_model_id)
        
        item = MyModel.get_by_id(my_model_id)
        if not item:
            logger.warning("MyModel with ID %s not found", my_model_id)
            return {"message": "MyModel not found"}, 404
        
        schema = MyModelSchema(session=db.session)
        return schema.dump(item), 200
    
    @require_jwt_auth()
    @check_access_required("update")
    def put(self, my_model_id):
        """Update a MyModel item by ID (full update)."""
        logger.info("Updating MyModel with ID: %s", my_model_id)
        
        json_data = request.get_json()
        item = MyModel.get_by_id(my_model_id)
        if not item:
            logger.warning("MyModel with ID %s not found", my_model_id)
            return {"message": "MyModel not found"}, 404
        
        schema = MyModelSchema(session=db.session)
        
        try:
            updated_item = schema.load(json_data, instance=item)
            db.session.commit()
            return schema.dump(updated_item), 200
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"message": "Validation error", "errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
    
    @require_jwt_auth()
    @check_access_required("update")
    def patch(self, my_model_id):
        """Partially update a MyModel item by ID."""
        logger.info("Partially updating MyModel with ID: %s", my_model_id)
        
        json_data = request.get_json()
        item = MyModel.get_by_id(my_model_id)
        if not item:
            logger.warning("MyModel with ID %s not found", my_model_id)
            return {"message": "MyModel not found"}, 404
        
        schema = MyModelSchema(session=db.session, partial=True)
        
        try:
            updated_item = schema.load(json_data, instance=item, partial=True)
            db.session.commit()
            return schema.dump(updated_item), 200
        except ValidationError as err:
            logger.error("Validation error: %s", err.messages)
            return {"message": "Validation error", "errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
    
    @require_jwt_auth()
    @check_access_required("delete")
    def delete(self, my_model_id):
        """Delete a MyModel item by ID."""
        logger.info("Deleting MyModel with ID: %s", my_model_id)
        
        item = MyModel.get_by_id(my_model_id)
        if not item:
            logger.warning("MyModel with ID %s not found", my_model_id)
            return {"message": "MyModel not found"}, 404
        
        try:
            db.session.delete(item)
            db.session.commit()
            return {}, 204
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Integrity error: %s", str(e))
            return {"message": "Integrity error"}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Database error: %s", str(e))
            return {"message": "Database error"}, 500
```

4. **Register resource** in `app/routes.py`:

```python
# app/routes.py
from app.resources.my_resource import MyModelListResource, MyModelResource

def register_routes(app):
    api = Api(app)
    
    # ... existing resources
    
    # MyModel endpoints
    api.add_resource(MyModelListResource, "/my-models")
    api.add_resource(MyModelResource, "/my-models/<string:my_model_id>")
```

5. **Create migration** and **add tests**

## Database Migrations

### Creating Migrations

```bash
# Auto-generate migration from model changes
flask db migrate -m "Add my_table"

# Review the generated migration

# Apply migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Handling Relationships

```python
# Migration for foreign key relationships
def upgrade():
    op.create_table(
        'my_table',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['company_id'], 
            ['companies.id'],
            name='fk_my_table_company'
        )
    )
    
    # Add index for performance
    op.create_index(
        'ix_my_table_company_id',
        'my_table',
        ['company_id']
    )
```

## Common Tasks

### Working with Organizational Hierarchy

```python
# Get all descendants of a unit
def get_unit_descendants(unit_id: int) -> List[OrganizationUnit]:
    """Get all child units recursively."""
    unit = OrganizationUnit.query.get(unit_id)
    descendants = []
    
    def collect_children(parent):
        for child in parent.children:
            descendants.append(child)
            collect_children(child)
    
    collect_children(unit)
    return descendants

# Get path from root to unit
def get_unit_path(unit_id: int) -> List[OrganizationUnit]:
    """Get path from root to this unit."""
    path = []
    unit = OrganizationUnit.query.get(unit_id)
    
    while unit:
        path.insert(0, unit)
        unit = unit.parent
    
    return path
```

### Integrating with Guardian Service

```python
import requests
from flask import current_app

def assign_role_to_user(user_id: int, role_id: int):
    """Assign a role to user via Guardian Service."""
    guardian_url = current_app.config['GUARDIAN_SERVICE_URL']
    internal_token = current_app.config['INTERNAL_AUTH_TOKEN']
    
    response = requests.post(
        f"{guardian_url}/user-roles",
        json={
            'user_id': user_id,
            'role_id': role_id
        },
        headers={
            'Authorization': f'Bearer {internal_token}'
        }
    )
    
    response.raise_for_status()
    return response.json()
```

## Service-Specific Guidelines

### Multi-tenancy Considerations

All resources should be scoped by `company_id`. The `@require_jwt_auth()` decorator automatically extracts `company_id` from the JWT token and stores it in `g.company_id`:

```python
# Example: Filter users by company from JWT context
class UserListResource(Resource):
    @require_jwt_auth()
    @check_access_required("list")
    def get(self):
        """Get all users from the authenticated user's company."""
        # company_id is automatically injected by @require_jwt_auth()
        company_id = g.company_id
        users = User.query.filter_by(company_id=company_id).all()
        schema = UserSchema(many=True)
        return schema.dump(users), 200
```

### Data Validation

Use Marshmallow schemas for validation in Flask-RESTful resources:

```python
from marshmallow import ValidationError
from flask_restful import Resource

class UserListResource(Resource):
    @require_jwt_auth()
    @check_access_required("create")
    def post(self):
        """Create a new user with schema validation."""
        json_data = request.get_json()
        user_schema = UserSchema(session=db.session)
        
        try:
            new_user = user_schema.load(json_data)
            db.session.add(new_user)
            db.session.commit()
            return user_schema.dump(new_user), 201
        except ValidationError as e:
            logger.error("Validation error: %s", e.messages)
            return {"message": "Validation error", "errors": e.messages}, 400
```

### Integration Points

This service communicates with:
- **Auth Service** (port 5001): Receives password verification requests
- **Guardian Service** (port 5003): User-role assignments, permission checks

## Getting Help

- **Main Project**: See [root CONTRIBUTING.md](https://github.com/bengeek06/waterfall/blob/main/CONTRIBUTING.md)
- **Issues**: Use GitHub issues with `service:identity` label
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Documentation**: [README.md](README.md)
- **OpenAPI Spec**: [openapi.yml](openapi.yml)

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Marshmallow Documentation](https://marshmallow.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)

---

**Remember**: Always refer to the [main CONTRIBUTING.md](https://github.com/bengeek06/waterfall/blob/main/CONTRIBUTING.md) for branch strategy, commit conventions, and pull request process!
