#!/bin/bash
# RAG Cache Health Check Script
# Usage: ./scripts/health_check.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_passed() { echo -e "${GREEN}✓${NC} $1"; }
check_failed() { echo -e "${RED}✗${NC} $1"; }
check_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Check API health
check_api() {
    echo "Checking API health..."

    RESPONSE=$(curl -sf "$BASE_URL/health" 2>/dev/null) || {
        check_failed "API is not responding"
        return 1
    }

    STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null || echo "unknown")

    if [ "$STATUS" == "healthy" ]; then
        check_passed "API is healthy"
    elif [ "$STATUS" == "degraded" ]; then
        check_warning "API is degraded"
    else
        check_failed "API status: $STATUS"
        return 1
    fi
}

# Check Redis connection
check_redis() {
    echo "Checking Redis..."

    RESPONSE=$(curl -sf "$BASE_URL/health" 2>/dev/null) || return 1
    REDIS_STATUS=$(echo "$RESPONSE" | jq -r '.redis // .services.redis // "unknown"' 2>/dev/null)

    if [ "$REDIS_STATUS" == "connected" ] || [ "$REDIS_STATUS" == "healthy" ]; then
        check_passed "Redis is connected"
    else
        check_failed "Redis status: $REDIS_STATUS"
        return 1
    fi
}

# Check Qdrant connection
check_qdrant() {
    echo "Checking Qdrant..."

    RESPONSE=$(curl -sf "$BASE_URL/health" 2>/dev/null) || return 1
    QDRANT_STATUS=$(echo "$RESPONSE" | jq -r '.qdrant // .services.qdrant // "unknown"' 2>/dev/null)

    if [ "$QDRANT_STATUS" == "connected" ] || [ "$QDRANT_STATUS" == "healthy" ]; then
        check_passed "Qdrant is connected"
    else
        check_failed "Qdrant status: $QDRANT_STATUS"
        return 1
    fi
}

# Check metrics endpoint
check_metrics() {
    echo "Checking metrics..."

    if curl -sf "$BASE_URL/metrics" > /dev/null 2>&1; then
        check_passed "Metrics endpoint is available"
    else
        check_warning "Metrics endpoint not available"
    fi
}

# Check cache stats
check_cache() {
    echo "Checking cache..."

    RESPONSE=$(curl -sf "$BASE_URL/api/v1/cache/stats" 2>/dev/null) || {
        check_warning "Cache stats not available"
        return 0
    }

    HIT_RATE=$(echo "$RESPONSE" | jq -r '.hit_rate // 0' 2>/dev/null)

    if (( $(echo "$HIT_RATE > 0.3" | bc -l 2>/dev/null || echo "0") )); then
        check_passed "Cache hit rate: ${HIT_RATE}%"
    elif (( $(echo "$HIT_RATE > 0" | bc -l 2>/dev/null || echo "0") )); then
        check_warning "Low cache hit rate: ${HIT_RATE}%"
    else
        check_warning "No cache data yet"
    fi
}

# Main health check
main() {
    echo "================================"
    echo "RAG Cache Health Check"
    echo "================================"
    echo ""

    ERRORS=0

    check_api || ((ERRORS++))
    check_redis || ((ERRORS++))
    check_qdrant || ((ERRORS++))
    check_metrics
    check_cache

    echo ""
    echo "================================"

    if [ $ERRORS -eq 0 ]; then
        check_passed "All critical checks passed"
        exit 0
    else
        check_failed "$ERRORS critical check(s) failed"
        exit 1
    fi
}

main

