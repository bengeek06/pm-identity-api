#!/bin/bash
#
# run-integration-tests.sh
# ------------------------
# Helper script to run integration tests with Docker services
#
# Usage:
#   ./run-integration-tests.sh                    # Run with default config
#   ./run-integration-tests.sh --with-guardian    # Include Guardian service
#   ./run-integration-tests.sh --build-local      # Build from local repos
#   ./run-integration-tests.sh --help             # Show usage

set -e

COMPOSE_FILE="docker-compose.integration.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WITH_GUARDIAN=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-guardian)
            WITH_GUARDIAN=false
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-guardian    Skip Guardian service (Guardian tests will be skipped)"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                     # Build all services locally, include Guardian"
            echo "  $0 --skip-guardian     # Build all services locally, skip Guardian"
            echo ""
            echo "Note: All services are always built from local repositories (../service_name)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

cd "$SCRIPT_DIR"

# Load .env.integration if exists
if [ -f ".env.integration" ]; then
    set -a
    source .env.integration
    set +a
fi

echo "🔨 Building services from local repositories..."
echo "   MinIO: Official image (always)"
echo "   Storage: ${STORAGE_SERVICE_PATH:-../storage_service}"
echo "   Guardian: ${GUARDIAN_SERVICE_PATH:-../guardian_service}"

echo "======================================"
echo "Integration Test Runner"
echo "======================================"

# Function to cleanup services
cleanup() {
    echo ""
    echo "🧹 Cleaning up services..."
    docker compose -f "$COMPOSE_FILE" --profile guardian down -v
}

# Trap EXIT to ensure cleanup
trap cleanup EXIT

# Check if services are already running
if docker compose -f "$COMPOSE_FILE" --profile guardian ps | grep -q "Up"; then
    echo "⚠️  Services already running. Stopping and removing volumes..."
    docker compose -f "$COMPOSE_FILE" --profile guardian down -v
fi

# Start services (build + up)
echo "🚀 Starting integration services (MinIO + Storage + Guardian)..."
if [ "$WITH_GUARDIAN" = true ]; then
    docker compose -f "$COMPOSE_FILE" --profile guardian up -d --build
else
    docker compose -f "$COMPOSE_FILE" up -d --build
fi

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
        minio_health=$(docker compose -f "$COMPOSE_FILE" ps minio | grep -c "healthy" || echo "0")
        storage_health=$(docker compose -f "$COMPOSE_FILE" ps storage-service | grep -c "healthy" || echo "0")
        
        # Remove any whitespace/newlines from health counts
        minio_health=$(echo "$minio_health" | tr -d '\n\r ')
        storage_health=$(echo "$storage_health" | tr -d '\n\r ')
        
        if [ "$WITH_GUARDIAN" = true ]; then
            guardian_health=$(docker compose -f "$COMPOSE_FILE" ps guardian-service | grep -c "healthy" || echo "0")
            guardian_health=$(echo "$guardian_health" | tr -d '\n\r ')
            if [ "$minio_health" -ge 1 ] && [ "$storage_health" -ge 1 ] && [ "$guardian_health" -ge 1 ]; then
                echo "✅ All services are healthy!"
                break
            fi
        else
            if [ "$minio_health" -ge 1 ] && [ "$storage_health" -ge 1 ]; then
                echo "✅ All services are healthy!"
                break
            fi
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
export GUARDIAN_SERVICE_URL="http://localhost:5002"
export USE_STORAGE_SERVICE="true"
export USE_GUARDIAN_SERVICE="true"
export JWT_SECRET="integration-test-secret-key"
export DATABASE_URL="sqlite:///:memory:"
export FLASK_ENV="testing"

# Run integration tests
echo ""
echo "🧪 Running integration tests..."
echo "======================================"

# Use pytest from virtual environment if available
if [ -f "venv/bin/pytest" ]; then
    PYTEST_CMD="venv/bin/pytest"
elif command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
else
    echo "❌ pytest not found. Please install it or activate your virtual environment."
    exit 1
fi

if $PYTEST_CMD -m integration -v "$@"; then
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
