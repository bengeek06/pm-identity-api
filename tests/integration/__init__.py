"""
Integration tests package.

These tests require external services (MinIO, Storage Service) to be running.
Run them with: pytest -m integration

To start services:
    docker-compose -f docker-compose.integration.yml up -d

To stop services:
    docker-compose -f docker-compose.integration.yml down
"""
