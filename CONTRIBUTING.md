# Contributing to Identity Service

Thank you for your interest in contributing to the **Identity Service**!

> **Note**: This service is part of the larger [Waterfall](../../README.md) project. For the overall development workflow, branch strategy, and contribution guidelines, please refer to the [main CONTRIBUTING.md](../../CONTRIBUTING.md) in the root repository.

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
- Flask 3.1+ for REST API
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
flask db upgrade

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
black app/ tests/

# Check without modifying
black --check app/ tests/
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

**Resource/Endpoint Structure:**
```python
# app/resources/users.py
from flask import Blueprint, request, jsonify
from app.models import User, db
from app.schemas import UserSchema
from app.logger import logger

users_bp = Blueprint('users', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)

@users_bp.route('/users', methods=['GET'])
def get_users():
    """Get list of users with optional filtering."""
    try:
        company_id = request.args.get('company_id', type=int)
        query = User.query
        
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        users = query.all()
        return jsonify(users_schema.dump(users)), 200
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch users"}), 500
```

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
from flask import Blueprint, request, jsonify
from app.models import MyModel, db
from app.schemas import MyModelSchema

my_resource_bp = Blueprint('my_resource', __name__)
schema = MyModelSchema()
schemas = MyModelSchema(many=True)

@my_resource_bp.route('/my-resources', methods=['GET', 'POST'])
def handle_my_resources():
    if request.method == 'GET':
        items = MyModel.query.all()
        return jsonify(schemas.dump(items)), 200
    
    elif request.method == 'POST':
        data = schema.load(request.json)
        item = MyModel(**data)
        db.session.add(item)
        db.session.commit()
        return jsonify(schema.dump(item)), 201
```

4. **Register blueprint** in `app/routes.py`

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

All resources should be scoped by `company_id`:

```python
# Always filter by company in queries
@users_bp.route('/users', methods=['GET'])
@require_company_context
def get_users():
    company_id = g.company_id  # From auth context
    users = User.query.filter_by(company_id=company_id).all()
    return jsonify(users_schema.dump(users)), 200
```

### Data Validation

Use Marshmallow schemas for validation:

```python
from marshmallow import ValidationError

@users_bp.route('/users', methods=['POST'])
def create_user():
    try:
        data = user_schema.load(request.json)
        # Create user
    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400
```

### Integration Points

This service communicates with:
- **Auth Service** (port 5001): Receives password verification requests
- **Guardian Service** (port 5003): User-role assignments, permission checks

## Getting Help

- **Main Project**: See [root CONTRIBUTING.md](../../CONTRIBUTING.md)
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

**Remember**: Always refer to the [main CONTRIBUTING.md](../../CONTRIBUTING.md) for branch strategy, commit conventions, and pull request process!
