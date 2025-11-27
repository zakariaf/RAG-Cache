# RAG Cache Security Best Practices

## Table of Contents

- [Security Overview](#security-overview)
- [Authentication & Authorization](#authentication--authorization)
- [API Security](#api-security)
- [Data Protection](#data-protection)
- [Infrastructure Security](#infrastructure-security)
- [Secrets Management](#secrets-management)
- [Monitoring & Auditing](#monitoring--auditing)
- [Security Checklist](#security-checklist)

## Security Overview

RAG Cache handles potentially sensitive user queries and LLM responses. This guide covers security best practices for production deployments.

### Security Principles

1. **Defense in Depth**: Multiple security layers
2. **Least Privilege**: Minimal permissions
3. **Zero Trust**: Verify everything
4. **Encrypt Everything**: At rest and in transit

## Authentication & Authorization

### API Key Authentication

```bash
# Enable API key authentication
API_KEY_ENABLED=true

# Set API keys (comma-separated for multiple)
API_KEYS=key1-xxxxx,key2-xxxxx,key3-xxxxx

# Client usage
curl -H "X-API-Key: key1-xxxxx" \
  http://localhost:8000/api/v1/query
```

### JWT Authentication (Future)

```python
# Example JWT configuration
JWT_SECRET_KEY=your-256-bit-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| `user` | Query, read cache |
| `admin` | All user + clear cache, view metrics |
| `superadmin` | All admin + manage users |

## API Security

### Rate Limiting

```bash
# Enable rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100    # Requests per window
RATE_LIMIT_WINDOW=60       # Window in seconds

# Per-IP rate limiting
RATE_LIMIT_BY_IP=true

# Per-API-key rate limiting
RATE_LIMIT_BY_KEY=true
```

### Request Validation

```python
# All inputs are validated via Pydantic
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    semantic_threshold: float = Field(ge=0.0, le=1.0)
```

### CORS Configuration

```bash
# Restrict CORS origins (production)
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,DELETE
CORS_ALLOW_HEADERS=Authorization,Content-Type,X-API-Key
```

### Input Sanitization

```python
# Queries are normalized and sanitized
def sanitize_query(query: str) -> str:
    # Remove control characters
    # Normalize whitespace
    # Limit length
    return normalized_query
```

### Security Headers

```python
# Applied via middleware
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}
```

## Data Protection

### Encryption in Transit

```bash
# Always use HTTPS in production
# nginx.conf
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

### Encryption at Rest

```bash
# Redis encryption (Enterprise feature)
# Or use encrypted storage volumes

# Qdrant storage encryption
# Mount encrypted volume for /qdrant/storage
```

### PII Handling

```python
# Don't log sensitive data
logger.info("Query processed", 
    query_hash=hash(query),  # Hash, not raw query
    user_id=user.id
)

# Redact PII from cache if needed
def redact_pii(text: str) -> str:
    # Redact emails, phone numbers, etc.
    return redacted_text
```

### Data Retention

```bash
# Limit cache TTL for data minimization
CACHE_TTL=3600  # 1 hour

# Implement data deletion on request
curl -X DELETE /api/v1/user/data
```

## Infrastructure Security

### Network Security

```yaml
# docker-compose.yml
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
      - internal  # Only internal access
  
  qdrant:
    networks:
      - internal  # Only internal access
```

### Container Security

```dockerfile
# Run as non-root user
FROM python:3.11-slim
RUN useradd -m -s /bin/bash appuser
USER appuser

# Read-only filesystem where possible
docker run --read-only ...

# No privileged mode
docker run --security-opt no-new-privileges ...
```

### Redis Security

```bash
# redis.conf
requirepass your-strong-password
bind 127.0.0.1  # Only local connections

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
rename-command DEBUG ""
```

### Qdrant Security

```bash
# Enable API key
QDRANT_API_KEY=your-api-key

# Restrict network access
# Only accessible from application network
```

## Secrets Management

### Environment Variables

```bash
# Never commit .env files
# .gitignore
.env
.env.local
.env.production

# Use .env.example as template (no real secrets)
OPENAI_API_KEY=your-key-here
```

### Secret Rotation

```bash
# Rotate API keys regularly
# 1. Generate new key
# 2. Update configuration
# 3. Deploy update
# 4. Revoke old key

# Automated rotation (future)
SECRET_ROTATION_DAYS=90
```

### Vault Integration (Enterprise)

```python
# Example HashiCorp Vault integration
import hvac

client = hvac.Client(url='https://vault.example.com')
secrets = client.secrets.kv.read_secret_version(
    path='ragcache/production'
)
openai_key = secrets['data']['data']['openai_api_key']
```

### AWS Secrets Manager

```python
import boto3

client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='ragcache/production')
secrets = json.loads(response['SecretString'])
```

## Monitoring & Auditing

### Access Logging

```python
# Log all API requests
logger.info("API request",
    method=request.method,
    path=request.path,
    user_id=user.id,
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    status_code=response.status_code,
    duration_ms=duration
)
```

### Security Events

```python
# Log security-relevant events
logger.warning("Authentication failed",
    ip=request.client.host,
    reason="invalid_api_key"
)

logger.warning("Rate limit exceeded",
    ip=request.client.host,
    user_id=user.id
)

logger.critical("Possible attack detected",
    ip=request.client.host,
    pattern="sql_injection_attempt"
)
```

### Alert Configuration

```yaml
# Alert on security events
alerts:
  - name: high_auth_failures
    condition: auth_failures_5m > 100
    severity: critical
    
  - name: unusual_traffic
    condition: requests_per_minute > normal_baseline * 10
    severity: warning
```

### Audit Trail

```python
# Audit log for sensitive operations
audit_log.record(
    action="cache_cleared",
    actor=user.id,
    timestamp=datetime.utcnow(),
    details={"entries_deleted": count}
)
```

## Security Checklist

### Development

- [ ] No secrets in code or version control
- [ ] Dependencies scanned for vulnerabilities
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] Debug mode disabled in production config

### Deployment

- [ ] HTTPS/TLS enabled
- [ ] API authentication enabled
- [ ] Rate limiting configured
- [ ] CORS restricted to known origins
- [ ] Security headers configured
- [ ] Non-root container user
- [ ] Minimal container permissions

### Infrastructure

- [ ] Network segmentation (internal/external)
- [ ] Redis password configured
- [ ] Qdrant API key configured
- [ ] Firewall rules configured
- [ ] Encrypted storage volumes
- [ ] Regular security updates

### Operations

- [ ] Access logging enabled
- [ ] Security monitoring configured
- [ ] Incident response plan documented
- [ ] Regular security audits scheduled
- [ ] Secret rotation procedure defined
- [ ] Backup encryption enabled

### Compliance

- [ ] Data retention policy defined
- [ ] PII handling documented
- [ ] GDPR requirements addressed (if applicable)
- [ ] SOC 2 controls (if applicable)
- [ ] Regular compliance reviews

## Vulnerability Reporting

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email security@example.com with details
3. Include steps to reproduce
4. Allow 90 days for fix before disclosure

---

**Last Updated:** November 2025

