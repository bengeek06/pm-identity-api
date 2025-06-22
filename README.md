# Identity Service API

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Flask](https://img.shields.io/badge/flask-%3E=2.0-green.svg)
![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)
![CI](https://img.shields.io/github/actions/workflow/status/<your-username>/flask_api_template/ci.yml?branch=main)
![Coverage](https://img.shields.io/badge/coverage-pytest-yellow.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

A production-ready API for managing users, companies, organizations, positions, subcontractors, and customers.  
This repository provides a solid foundation for your next identity or directory service, with environment-based configuration, Docker support, migrations, and a full OpenAPI 3.0 specification.

---

## Features

- **Environment-based configuration**: Easily switch between development, testing, staging, and production using the `FLASK_ENV` environment variable.
- **RESTful API**: CRUD endpoints for users, companies, organizations, positions, subcontractors, and customers.
- **OpenAPI 3.0 documentation**: See [`openapi.yml`](openapi.yml).
- **Docker-ready**: Includes a `Dockerfile` and healthcheck script.
- **Database migrations**: Managed with Alembic/Flask-Migrate.
- **Testing**: Pytest-based test suite.
- **Logging**: Colored logging for better readability.

---

## Environments

The application behavior is controlled by the `FLASK_ENV` environment variable.  
Depending on its value, different configuration classes and `.env` files are loaded:

- **development** (default):  
  Loads `.env.development` and uses `app.config.DevelopmentConfig`.  
  Debug mode is enabled.

- **testing**:  
  Loads `.env.test` and uses `app.config.TestingConfig`.  
  Testing mode is enabled.

- **staging**:  
  Loads `.env.staging` and uses `app.config.StagingConfig`.  
  Debug mode is enabled.

- **production**:  
  Loads `.env.production` and uses `app.config.ProductionConfig`.  
  Debug mode is disabled.

See `app/config.py` for details.  
You can use `env.example` as a template for your environment files.

---

## API Endpoints

The main endpoints are:

| Method | Path                                   | Description                                 |
|--------|----------------------------------------|---------------------------------------------|
| POST   | /users                                 | Create a new user                           |
| GET    | /users                                 | List users                                  |
| GET    | /users/{user_id}                       | Get user by ID                              |
| PUT    | /users/{user_id}                       | Update user by ID                           |
| PATCH  | /users/{user_id}                       | Partially update user by ID                 |
| DELETE | /users/{user_id}                       | Delete user by ID                           |
| POST   | /users/verify_password                 | Verify a user's password by email           |
| POST   | /companies                             | Create a new company                        |
| GET    | /companies                             | List companies                              |
| GET    | /companies/{company_id}                | Get company by ID                           |
| PUT    | /companies/{company_id}                | Update company by ID                        |
| PATCH  | /companies/{company_id}                | Partially update company by ID              |
| DELETE | /companies/{company_id}                | Delete company by ID                        |
| GET    | /companies/{company_id}/users          | List users in a company                     |
| POST   | /organizations                         | Create an organization unit                 |
| GET    | /organizations                         | List organization units                     |
| GET    | /organizations/{organization_id}       | Get organization unit by ID                 |
| PUT    | /organizations/{organization_id}       | Update organization unit by ID              |
| PATCH  | /organizations/{organization_id}       | Partially update organization unit by ID    |
| DELETE | /organizations/{organization_id}       | Delete organization unit by ID              |
| POST   | /positions                             | Create a new position                       |
| GET    | /positions                             | List positions                              |
| GET    | /positions/{position_id}               | Get position by ID                          |
| PUT    | /positions/{position_id}               | Update position by ID                       |
| PATCH  | /positions/{position_id}               | Partially update position by ID             |
| DELETE | /positions/{position_id}               | Delete position by ID                       |
| POST   | /subcontractors                        | Create a new subcontractor                  |
| GET    | /subcontractors                        | List subcontractors                         |
| GET    | /subcontractors/{subcontractor_id}     | Get subcontractor by ID                     |
| PUT    | /subcontractors/{subcontractor_id}     | Update subcontractor by ID                  |
| PATCH  | /subcontractors/{subcontractor_id}     | Partially update subcontractor by ID        |
| DELETE | /subcontractors/{subcontractor_id}     | Delete subcontractor by ID                  |
| POST   | /customers                             | Create a new customer                       |
| GET    | /customers                             | List customers                              |
| GET    | /customers/{customer_id}               | Get customer by ID                          |
| PUT    | /customers/{customer_id}               | Update customer by ID                       |
| PATCH  | /customers/{customer_id}               | Partially update customer by ID             |
| DELETE | /customers/{customer_id}               | Delete customer by ID                       |

See [`openapi.yml`](openapi.yml) for full documentation and schema details.

---

## Usage

### Local Development

1. Copy `env.example` to `.env.development` and set your variables.
2. Install dependencies:
   ```
   pip install -r requirements-dev.txt
   ```
3. Run database migrations:
   ```
   flask db upgrade
   ```
4. Start the server:
   ```
   FLASK_ENV=development python run.py
   ```

### Docker

Build and run the container:
```
docker build -t flask-api-template .
docker run --env-file .env.development -p 5000:5000 flask-api-template
```

### Testing

Run all tests with:
```
pytest
```

---

## License

This project is licensed under the GNU AGPLv3.
See [LICENSE](LICENSE) and [COMMERCIAL-LICENSE.txt](COMMERCIAL-LICENSE.txt) for details.


---

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
