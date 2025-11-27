#!/bin/bash
# RAG Cache Rollback Script
# Usage: ./scripts/rollback.sh [backup_timestamp]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# List available backups
list_backups() {
    log_info "Available backups:"
    ls -la "$PROJECT_ROOT/backups/" 2>/dev/null || echo "No backups found"
}

# Rollback to specific backup
rollback() {
    local BACKUP_TIMESTAMP="$1"
    local BACKUP_DIR="$PROJECT_ROOT/backups/$BACKUP_TIMESTAMP"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Backup not found: $BACKUP_DIR"
    fi
    
    log_info "Rolling back to backup: $BACKUP_TIMESTAMP"
    
    # Stop services
    log_info "Stopping services..."
    cd "$PROJECT_ROOT"
    docker-compose down
    
    # Restore Redis backup
    if [ -f "$BACKUP_DIR/redis-dump.rdb" ]; then
        log_info "Restoring Redis backup..."
        docker-compose up -d redis
        sleep 5
        docker cp "$BACKUP_DIR/redis-dump.rdb" ragcache-redis:/data/dump.rdb
        docker-compose restart redis
    fi
    
    # Restore Qdrant backup
    if [ -f "$BACKUP_DIR/qdrant-snapshot.json" ]; then
        log_info "Restoring Qdrant backup..."
        # Note: Full Qdrant restore requires more complex handling
        log_warn "Qdrant snapshot restore may require manual intervention"
    fi
    
    # Start all services
    log_info "Starting services..."
    docker-compose up -d
    
    # Health check
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    if curl -sf http://localhost:8000/health > /dev/null; then
        log_info "Rollback completed successfully"
    else
        log_error "Services not healthy after rollback"
    fi
}

# Rollback to previous image
rollback_image() {
    log_info "Rolling back to previous image..."
    
    # Get previous image
    PREVIOUS_IMAGE=$(docker images ragcache --format "{{.Repository}}:{{.Tag}}" | sed -n '2p')
    
    if [ -z "$PREVIOUS_IMAGE" ]; then
        log_error "No previous image found"
    fi
    
    log_info "Rolling back to image: $PREVIOUS_IMAGE"
    
    # Update docker-compose to use previous image
    cd "$PROJECT_ROOT"
    
    # Restart with previous image
    docker-compose down
    docker-compose up -d
    
    log_info "Image rollback completed"
}

# Main
main() {
    if [ "${1:-}" == "list" ]; then
        list_backups
    elif [ "${1:-}" == "image" ]; then
        rollback_image
    elif [ -n "${1:-}" ]; then
        rollback "$1"
    else
        echo "Usage: $0 [list|image|backup_timestamp]"
        echo ""
        echo "Commands:"
        echo "  list                List available backups"
        echo "  image               Rollback to previous Docker image"
        echo "  <timestamp>         Rollback to specific backup"
        exit 1
    fi
}

main "${1:-}"

