#!/bin/bash
# RAG Cache Production Deployment Script
# Usage: ./scripts/deploy.sh [environment]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Pre-deployment checks
preflight_check() {
    log_info "Running pre-deployment checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
    fi
    
    # Check environment file
    ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
    fi
    
    # Verify required environment variables
    source "$ENV_FILE"
    
    if [ -z "${OPENAI_API_KEY:-}" ]; then
        log_error "OPENAI_API_KEY is not set"
    fi
    
    log_info "Pre-deployment checks passed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    cd "$PROJECT_ROOT"
    
    docker build \
        --target production \
        -t ragcache:$TIMESTAMP \
        -t ragcache:latest \
        .
    
    log_info "Docker image built: ragcache:$TIMESTAMP"
}

# Run tests before deployment
run_tests() {
    log_info "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run unit tests
    docker run --rm ragcache:latest \
        python -m pytest tests/unit/ -v --no-cov || {
        log_error "Unit tests failed"
    }
    
    log_info "Tests passed"
}

# Create backup before deployment
create_backup() {
    log_info "Creating backup..."
    
    BACKUP_DIR="$PROJECT_ROOT/backups/$TIMESTAMP"
    mkdir -p "$BACKUP_DIR"
    
    # Backup Redis data if container exists
    if docker ps -a --format '{{.Names}}' | grep -q 'ragcache-redis'; then
        docker exec ragcache-redis redis-cli BGSAVE
        sleep 2
        docker cp ragcache-redis:/data/dump.rdb "$BACKUP_DIR/redis-dump.rdb" 2>/dev/null || true
    fi
    
    # Backup Qdrant data if container exists
    if docker ps -a --format '{{.Names}}' | grep -q 'ragcache-qdrant'; then
        curl -s -X POST http://localhost:6333/collections/ragcache/snapshots \
            -o "$BACKUP_DIR/qdrant-snapshot.json" 2>/dev/null || true
    fi
    
    log_info "Backup created at: $BACKUP_DIR"
}

# Deploy services
deploy() {
    log_info "Deploying services..."
    
    cd "$PROJECT_ROOT"
    
    # Set environment file
    export ENV_FILE=".env.$ENVIRONMENT"
    
    # Deploy with docker-compose
    docker-compose -f docker-compose.yml \
        --env-file "$ENV_FILE" \
        up -d --remove-orphans
    
    log_info "Services deployed"
}

# Health check
health_check() {
    log_info "Running health checks..."
    
    MAX_RETRIES=30
    RETRY_INTERVAL=2
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -sf http://localhost:8000/health > /dev/null; then
            log_info "Health check passed"
            return 0
        fi
        log_warn "Waiting for service to be healthy... ($i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
    
    log_error "Health check failed after $MAX_RETRIES attempts"
}

# Post-deployment verification
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check all services are running
    SERVICES=("ragcache-api" "ragcache-redis" "ragcache-qdrant")
    
    for service in "${SERVICES[@]}"; do
        if ! docker ps --format '{{.Names}}' | grep -q "$service"; then
            log_error "Service not running: $service"
        fi
    done
    
    # Test query endpoint
    RESPONSE=$(curl -sf -X POST http://localhost:8000/api/v1/query \
        -H "Content-Type: application/json" \
        -d '{"query": "test deployment", "use_cache": false}' 2>/dev/null) || {
        log_error "Query endpoint test failed"
    }
    
    log_info "Deployment verified successfully"
}

# Cleanup old images
cleanup() {
    log_info "Cleaning up old images..."
    
    # Keep last 3 images
    docker images ragcache --format "{{.ID}}" | tail -n +4 | xargs -r docker rmi 2>/dev/null || true
    
    # Remove dangling images
    docker image prune -f 2>/dev/null || true
    
    log_info "Cleanup completed"
}

# Main deployment flow
main() {
    log_info "Starting deployment to $ENVIRONMENT environment"
    
    preflight_check
    build_image
    run_tests
    create_backup
    deploy
    health_check
    verify_deployment
    cleanup
    
    log_info "Deployment completed successfully!"
    log_info "Timestamp: $TIMESTAMP"
}

# Run main
main

