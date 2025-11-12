# RAG Cache Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Environment Configuration](#environment-configuration)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Overview

This guide covers deploying RAG Cache in various environments, from local development to production cloud deployments.

### Deployment Options

| Environment | Complexity | Cost | Use Case |
|-------------|-----------|------|----------|
| Local Docker | Low | Free | Development, testing |
| Docker Compose | Low | Free | Small deployments, demos |
| Kubernetes | High | Variable | Production, scalable |
| Cloud Managed | Medium | $$$ | Production, fully managed |

## Development Deployment

### Prerequisites

- Python 3.11 or higher
- Docker 20.10+ and Docker Compose 2.0+
- Git
- 4GB RAM minimum
- OpenAI API key

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/RAG-Cache.git
cd RAG-Cache

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install-dev

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

# Start services
make docker-up

# Verify deployment
curl http://localhost:8000/health
```

### Verify Installation

```bash
# Check service status
make docker-ps

# View logs
make docker-logs

# Test query endpoint
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?"}' | jq
```

### Development Workflow

```bash
# Start development environment
make dev

# Run application with hot reload
make run

# Run tests
make test

# Format and lint
make quality

# Stop services
make docker-down
```

## Production Deployment

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
│                   (NGINX/Traefik)                       │
└────────────┬───────────────────────────┬────────────────┘
             │                           │
        ┌────▼────┐                 ┌────▼────┐
        │FastAPI 1│                 │FastAPI 2│
        │Container│                 │Container│
        └────┬────┘                 └────┬────┘
             │                           │
             └─────────┬─────────────────┘
                       │
            ┌──────────▼─────────┐
            │   Redis Cluster    │
            │   (Primary + Replica) │
            └────────────────────┘
            ┌────────────────────┐
            │  Qdrant Cluster    │
            │  (Multi-node)      │
            └────────────────────┘
```

### Pre-deployment Checklist

- [ ] Environment variables configured
- [ ] API keys securely stored
- [ ] Database backups configured
- [ ] Monitoring and logging set up
- [ ] SSL/TLS certificates obtained
- [ ] Load balancer configured
- [ ] Health checks enabled
- [ ] Rate limiting configured
- [ ] Security audit completed
- [ ] Disaster recovery plan documented

### Security Hardening

#### 1. Environment Variables

Never commit secrets to version control:

```bash
# .env (never commit this file)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
REDIS_PASSWORD=strong-password-here
SECRET_KEY=generate-strong-secret-key

# Generate strong secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 2. HTTPS/TLS

Always use HTTPS in production:

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/api.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourcompany.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://ragcache:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 3. Network Security

```yaml
# docker-compose.prod.yml
networks:
  internal:
    driver: bridge
    internal: true  # No external access
  external:
    driver: bridge

services:
  api:
    networks:
      - external
      - internal

  redis:
    networks:
      - internal  # Only accessible internally

  qdrant:
    networks:
      - internal  # Only accessible internally
```

#### 4. Resource Limits

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        max_attempts: 3
```

## Environment Configuration

### Environment Variables

#### Required Variables

```bash
# Application
APP_NAME=RAG-Cache
APP_VERSION=1.0.0
APP_ENV=production  # development, staging, production
LOG_LEVEL=INFO      # DEBUG, INFO, WARNING, ERROR, CRITICAL

# API Keys
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx  # Optional

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-strong-password
REDIS_DB=0
REDIS_POOL_SIZE=10
REDIS_SOCKET_TIMEOUT=5

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key  # Optional
QDRANT_COLLECTION_NAME=ragcache_embeddings

# Cache Configuration
CACHE_TTL=3600                    # Default TTL in seconds
SEMANTIC_THRESHOLD=0.85           # Default similarity threshold
MAX_CACHE_SIZE=10000             # Maximum cache entries

# Performance
UVICORN_WORKERS=4                # Number of worker processes
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_RELOAD=false             # Set to true for development

# Security
SECRET_KEY=generate-your-secret-key
CORS_ORIGINS=https://yourapp.com
ALLOWED_HOSTS=api.yourcompany.com,yourapp.com
```

#### Optional Variables

```bash
# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
METRICS_NAMESPACE=ragcache

# Logging
LOG_FORMAT=json                  # json or text
LOG_FILE=/var/log/ragcache/app.log
LOG_ROTATION=daily

# Rate Limiting (Future)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Feature Flags
ENABLE_SEMANTIC_CACHE=true
ENABLE_QUERY_LOGGING=true
ENABLE_METRICS=true
```

### Configuration Management

#### Development

```bash
# .env.development
APP_ENV=development
LOG_LEVEL=DEBUG
UVICORN_RELOAD=true
UVICORN_WORKERS=1
```

#### Staging

```bash
# .env.staging
APP_ENV=staging
LOG_LEVEL=INFO
UVICORN_RELOAD=false
UVICORN_WORKERS=2
```

#### Production

```bash
# .env.production
APP_ENV=production
LOG_LEVEL=WARNING
UVICORN_RELOAD=false
UVICORN_WORKERS=4
```

## Docker Deployment

### Production Dockerfile

The included `Dockerfile` has multi-stage builds:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
# ... build dependencies

# Production stage
FROM python:3.11-slim as production
# ... runtime only
```

### Build Production Image

```bash
# Build production image
docker build --target production -t ragcache:latest .

# Tag for registry
docker tag ragcache:latest your-registry.com/ragcache:1.0.0
docker tag ragcache:latest your-registry.com/ragcache:latest

# Push to registry
docker push your-registry.com/ragcache:1.0.0
docker push your-registry.com/ragcache:latest
```

### Docker Compose Production

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    image: your-registry.com/ragcache:latest
    restart: always
    env_file: .env.production
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - qdrant
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - ragcache-network
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  redis:
    image: redis:7.2-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    networks:
      - ragcache-network

  qdrant:
    image: qdrant/qdrant:v1.6.1
    restart: always
    volumes:
      - qdrant-data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - ragcache-network

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    networks:
      - ragcache-network

volumes:
  redis-data:
  qdrant-data:

networks:
  ragcache-network:
    driver: bridge
```

### Deploy with Docker Compose

```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale API instances
docker-compose -f docker-compose.prod.yml up -d --scale api=4

# Stop services
docker-compose -f docker-compose.prod.yml down
```

## Cloud Deployment

### AWS Deployment

#### Using ECS (Elastic Container Service)

```bash
# 1. Build and push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

docker build -t ragcache .
docker tag ragcache:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/ragcache:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ragcache:latest

# 2. Create ECS task definition
# See task-definition.json

# 3. Deploy to ECS
aws ecs update-service \
  --cluster ragcache-cluster \
  --service ragcache-service \
  --force-new-deployment
```

#### Using EC2 (Traditional)

```bash
# 1. Launch EC2 instance (Ubuntu 22.04)
# 2. SSH into instance
ssh -i key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# 3. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu

# 4. Clone and deploy
git clone https://github.com/your-org/RAG-Cache.git
cd RAG-Cache
cp .env.example .env
# Edit .env with production values
docker-compose -f docker-compose.prod.yml up -d
```

### Google Cloud Platform (GCP)

#### Using Cloud Run

```bash
# 1. Build and push to Container Registry
gcloud builds submit --tag gcr.io/your-project/ragcache

# 2. Deploy to Cloud Run
gcloud run deploy ragcache \
  --image gcr.io/your-project/ragcache \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-xxx \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10
```

#### Using GKE (Kubernetes)

See [Kubernetes Deployment](#kubernetes-deployment) section.

### Azure Deployment

#### Using Container Instances

```bash
# 1. Build and push to ACR
az acr build --registry ragcacheacr --image ragcache:latest .

# 2. Deploy to Container Instances
az container create \
  --resource-group ragcache-rg \
  --name ragcache-api \
  --image ragcacheacr.azurecr.io/ragcache:latest \
  --cpu 1 \
  --memory 1 \
  --port 8000 \
  --environment-variables \
    OPENAI_API_KEY=sk-xxx \
    REDIS_HOST=ragcache-redis.redis.cache.windows.net
```

### Kubernetes Deployment

#### Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ragcache-api
  labels:
    app: ragcache
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ragcache
  template:
    metadata:
      labels:
        app: ragcache
    spec:
      containers:
      - name: api
        image: your-registry.com/ragcache:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ragcache-secrets
              key: openai-api-key
        - name: REDIS_HOST
          value: redis-service
        - name: QDRANT_HOST
          value: qdrant-service
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: ragcache-service
spec:
  selector:
    app: ragcache
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace ragcache

# Create secrets
kubectl create secret generic ragcache-secrets \
  --from-literal=openai-api-key=sk-xxx \
  --namespace ragcache

# Apply manifests
kubectl apply -f k8s/ --namespace ragcache

# Check status
kubectl get pods --namespace ragcache
kubectl get services --namespace ragcache

# View logs
kubectl logs -f deployment/ragcache-api --namespace ragcache
```

## Monitoring and Maintenance

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check (future)
curl http://localhost:8000/health?detailed=true
```

### Logging

#### Structured Logging

Application uses structured logging:

```json
{
  "timestamp": "2025-11-11T10:30:00.123Z",
  "level": "INFO",
  "logger": "app.services.query_service",
  "message": "Query processed",
  "query_hash": "abc123",
  "cache_hit": true,
  "latency_ms": 45
}
```

#### Log Aggregation

**Using CloudWatch (AWS):**

```bash
# Install CloudWatch agent
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure agent to collect logs
# See cloudwatch-config.json
```

**Using ELK Stack:**

```yaml
# docker-compose.prod.yml (add)
services:
  elasticsearch:
    image: elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
    volumes:
      - es-data:/usr/share/elasticsearch/data

  logstash:
    image: logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: kibana:8.5.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### Metrics (Future Feature)

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/metrics

# Example metrics:
# ragcache_queries_total{provider="openai",cache_hit="true"} 150
# ragcache_query_duration_seconds_bucket{le="0.1"} 120
# ragcache_cache_size 1500
```

### Backup and Recovery

#### Redis Backup

```bash
# Manual backup
docker exec redis redis-cli BGSAVE

# Automated backup (cron)
0 2 * * * docker exec redis redis-cli BGSAVE
0 3 * * * cp /var/lib/docker/volumes/redis-data/_data/dump.rdb \
  /backups/redis-$(date +\%Y\%m\%d).rdb
```

#### Qdrant Backup

```bash
# Create snapshot
curl -X POST http://localhost:6333/collections/ragcache_embeddings/snapshots

# Download snapshot
curl http://localhost:6333/collections/ragcache_embeddings/snapshots/{snapshot-name} \
  -o /backups/qdrant-$(date +%Y%m%d).snapshot

# Restore snapshot
curl -X PUT http://localhost:6333/collections/ragcache_embeddings/snapshots/upload \
  --data-binary @/backups/qdrant-20251111.snapshot
```

### Updates and Maintenance

```bash
# Zero-downtime deployment
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api

# Database migration (if needed)
docker-compose -f docker-compose.prod.yml run --rm api \
  python -m app.scripts.migrate

# Clear cache
curl -X DELETE http://localhost:8000/api/v1/cache
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
docker-compose logs api

# Common causes:
# - Missing environment variables
# - Port already in use
# - Invalid API keys
# - Network issues

# Solution:
docker-compose down
# Fix configuration
docker-compose up -d
```

#### 2. Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
# Should return: PONG

# Check password
docker-compose exec redis redis-cli -a your-password ping
```

#### 3. Qdrant Connection Failed

```bash
# Check Qdrant is running
docker-compose ps qdrant

# Test connection
curl http://localhost:6333/health
# Should return: {"status":"ok"}

# Check collections
curl http://localhost:6333/collections
```

#### 4. Slow Query Performance

```bash
# Check cache hit rate
curl http://localhost:8000/api/v1/cache/stats

# Low hit rate causes:
# - Semantic threshold too high
# - Cache too small
# - TTL too short

# Solutions:
# - Lower semantic_threshold (e.g., 0.80)
# - Increase MAX_CACHE_SIZE
# - Increase CACHE_TTL
```

#### 5. High Memory Usage

```bash
# Check memory usage
docker stats

# Solutions:
# - Reduce REDIS_POOL_SIZE
# - Reduce MAX_CACHE_SIZE
# - Reduce UVICORN_WORKERS
# - Add memory limits in docker-compose
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug
docker-compose -f docker-compose.prod.yml up

# Watch logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### Performance Tuning

```bash
# Tune Redis
# redis.conf additions:
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-backlog 511

# Tune Uvicorn workers
# More workers = higher throughput
# Rule of thumb: (2 × CPU cores) + 1
export UVICORN_WORKERS=9  # For 4-core machine

# Tune connection pools
export REDIS_POOL_SIZE=20
```

## Security Checklist

Production deployment security checklist:

- [ ] All secrets in environment variables (not code)
- [ ] HTTPS/TLS enabled
- [ ] Firewall configured (only required ports open)
- [ ] Redis password protected
- [ ] Qdrant API key configured
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] Regular security updates
- [ ] Monitoring and alerting configured
- [ ] Backup and recovery tested
- [ ] Incident response plan documented
- [ ] Access logs enabled
- [ ] Regular security audits scheduled

## Support

For deployment issues:

1. Check [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
2. Check [API.md](./API.md) for endpoint documentation
3. Review logs: `docker-compose logs`
4. Open an issue on GitHub with:
   - Deployment environment
   - Error messages
   - Configuration (redact secrets!)
   - Steps to reproduce

---

**Last Updated:** November 11, 2025
