# RAG Cache Production Launch Checklist

## Pre-Launch Checklist

### Infrastructure
- [ ] Production server provisioned
- [ ] Docker and Docker Compose installed
- [ ] Sufficient disk space for data volumes
- [ ] Network firewall configured (ports 80, 443)
- [ ] DNS configured for domain

### Security
- [ ] `.env.production` configured with real values
- [ ] Strong Redis password set
- [ ] API keys rotated and stored securely
- [ ] SSL/TLS certificates obtained
- [ ] CORS origins restricted to production domains
- [ ] Rate limiting configured
- [ ] Security headers enabled

### Monitoring
- [ ] Prometheus/Grafana configured (optional)
- [ ] Alerting configured (email/Slack)
- [ ] Log aggregation setup (optional)
- [ ] Health check monitoring configured

### Backup
- [ ] Automated Redis backup configured
- [ ] Qdrant snapshot strategy defined
- [ ] Backup retention policy set
- [ ] Recovery procedure tested

### Documentation
- [ ] Runbook created
- [ ] Incident response plan documented
- [ ] Contact list updated
- [ ] Change log updated

---

## Launch Day

### Pre-Deployment (T-2 hours)
- [ ] Run final tests on staging
- [ ] Verify all secrets are configured
- [ ] Notify stakeholders
- [ ] Prepare rollback plan

### Deployment (T-0)
```bash
# 1. Run deployment
./scripts/deploy.sh production

# 2. Verify health
./scripts/health_check.sh

# 3. Smoke test
curl -X POST https://your-domain.com/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"query": "test"}'
```

### Post-Deployment (T+1 hour)
- [ ] Monitor error rates
- [ ] Check cache hit rates
- [ ] Verify logging is working
- [ ] Confirm metrics collection
- [ ] Test alerting

---

## Post-Launch Monitoring

### Daily Checks
- [ ] Review error logs
- [ ] Check cache hit rate
- [ ] Monitor response times
- [ ] Verify backup completion

### Weekly Tasks
- [ ] Review cost metrics (LLM usage)
- [ ] Analyze query patterns
- [ ] Check disk usage
- [ ] Review security logs

### Monthly Tasks
- [ ] Security updates
- [ ] Dependency updates
- [ ] Performance review
- [ ] Capacity planning

---

## Rollback Procedure

If issues occur:

```bash
# 1. Rollback to previous image
./scripts/rollback.sh image

# 2. Or rollback to specific backup
./scripts/rollback.sh list
./scripts/rollback.sh 20251127_120000

# 3. Verify health
./scripts/health_check.sh
```

---

## Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | TBD | TBD |
| Team Lead | TBD | TBD |
| Infrastructure | TBD | TBD |

---

## Success Criteria

Launch is successful when:
- [ ] API responds with 200 OK
- [ ] Cache operations work
- [ ] LLM queries complete
- [ ] Error rate < 1%
- [ ] P95 latency < 2s
- [ ] All alerts clear

---

**Checklist Version:** 1.0.0
**Last Updated:** November 2025

