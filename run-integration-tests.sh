#!/bin/bash
#
# run-integration-tests.sh
# ------------------------
# Helper script to run integration tests with Docker services
#

set -e

COMPOSE_FILE="docker-compose.integration.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

echo "======================================"
echo "Integration Test Runner"
echo "======================================"

# Function to cleanup services
cleanup() {
    echo ""
    echo "🧹 Cleaning up services..."
    docker compose -f "$COMPOSE_FILE" down -v
}

# Trap EXIT to ensure cleanup
trap cleanup EXIT

# Check if services are already running
if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo "⚠️  Services already running. Stopping..."
    docker compose -f "$COMPOSE_FILE" down
fi

# Start services
echo "🚀 Starting MinIO and Storage Service..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
        minio_health=$(docker compose -f "$COMPOSE_FILE" ps minio | grep -c "healthy" || echo "0")
        storage_health=$(docker compose -f "$COMPOSE_FILE" ps storage-service | grep -c "healthy" || echo "0")
        
        if [ "$minio_health" -ge 1 ] && [ "$storage_health" -ge 1 ]; then
            echo "✅ All services are healthy!"
            break
        fi
    fi
    
    sleep 2
    elapsed=$((elapsed + 2))
    echo "   ... waiting ($elapsed/$timeout seconds)"
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ Services failed to become healthy within $timeout seconds"
    echo ""
    echo "Service status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    echo "Logs:"
    docker compose -f "$COMPOSE_FILE" logs
    exit 1
fi

# Show service status
echo ""
echo "📊 Service Status:"
docker compose -f "$COMPOSE_FILE" ps

# Export environment variables for integration tests
export STORAGE_SERVICE_URL="http://localhost:5001"
export USE_STORAGE_SERVICE="true"
export JWT_SECRET="integration-test-secret-key"
export DATABASE_URL="sqlite:///:memory:"
export FLASK_ENV="testing"

# Run integration tests
echo ""
echo "🧪 Running integration tests..."
echo "======================================"

if pytest -m integration -v "$@"; then
    echo ""
    echo "✅ All integration tests passed!"
    exit_code=0
else
    echo ""
    echo "❌ Some integration tests failed"
    exit_code=1
fi

# Show logs if tests failed
if [ $exit_code -ne 0 ]; then
    echo ""
    echo "📜 Service Logs:"
    echo "======================================"
    docker compose -f "$COMPOSE_FILE" logs --tail=50
fi

exit $exit_code
