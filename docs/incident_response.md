# Incident Response Runbook

## Incident Classification

### Severity Levels

- **P0 - Critical**: Complete system outage, data loss, security breach
- **P1 - High**: Major functionality broken, significant user impact
- **P2 - Medium**: Partial functionality loss, degraded performance
- **P3 - Low**: Minor issues, cosmetic problems

## Response Process

### 1. Detection

Incidents are detected through:
- Monitoring alerts (PagerDuty/Slack)
- User reports
- Automated health checks
- Log analysis

### 2. Initial Assessment (15 minutes)

**Responder Actions:**
1. Acknowledge the alert
2. Assess impact and severity
3. Notify stakeholders if P0/P1
4. Start incident channel in Slack

**Information to gather:**
- When did it start?
- What's affected?
- How many users impacted?
- Recent deployments/changes?

### 3. Investigation (30-60 minutes)

**Check primary systems:**
1. Application logs: `kubectl logs` or log aggregation
2. Metrics: Grafana/Prometheus dashboards
3. Health endpoints: `/health`
4. External dependencies: Redis, LLM providers

**Common investigation commands:**
```bash
# Check application status
curl -f https://api.example.com/health

# Recent errors
kubectl logs deployment/ai-support-agent --since=1h | grep ERROR

# LLM provider status
curl -H "Authorization: Bearer $API_KEY" https://api.openai.com/v1/models
```

### 4. Mitigation (1-4 hours)

**Common mitigations:**

#### LLM Provider Outage
```bash
# Switch to fallback provider
kubectl set env deployment/ai-support-agent FALLBACK_PROVIDER=anthropic

# Restart deployment
kubectl rollout restart deployment/ai-support-agent
```

#### Memory Issues
```bash
# Clear sessions if needed
kubectl exec -it deployment/redis -- redis-cli FLUSHALL

# Scale up memory
kubectl scale deployment/ai-support-agent --replicas=3
```

#### Vector Store Issues
```bash
# Rebuild index
kubectl exec -it job/rebuild-index -- python scripts/rebuild_index.py
```

### 5. Resolution

**Verify fix:**
- Health checks pass
- Metrics return to normal
- User functionality restored

**Document root cause and fix**

### 6. Post-Mortem (24 hours)

**Conduct blameless post-mortem:**
- Timeline of events
- Root cause analysis
- Impact assessment
- Prevention measures
- Action items

## Specific Incident Types

### Complete Outage

**Symptoms:** 5xx errors, health check fails

**Immediate actions:**
1. Check pod status: `kubectl get pods`
2. Check logs: `kubectl logs`
3. Restart deployment: `kubectl rollout restart`
4. Check dependencies (Redis, ChromaDB)

### High Latency

**Symptoms:** P95 latency > 10s

**Investigation:**
1. Check LLM provider latency
2. Monitor Redis performance
3. Review vector search performance
4. Check memory usage

**Mitigation:**
- Scale horizontally
- Switch to faster LLM model
- Optimize queries

### Data Loss

**Symptoms:** Sessions missing, knowledge base empty

**Immediate actions:**
1. Check backups
2. Restore from backup if available
3. Rebuild knowledge base from source
4. Communicate with users

### Security Incident

**Symptoms:** Unauthorized access, data breach

**Immediate actions:**
1. Rotate all API keys
2. Audit access logs
3. Notify affected users
4. Involve security team

## Communication

### Internal Communication

- Use dedicated Slack channel for incident
- Keep stakeholders updated every 30 minutes for P0/P1
- Use status page for external communication

### External Communication

- Update status page with incident details
- Send email notifications for prolonged outages
- Provide ETA when possible

## Prevention

### Proactive Measures

1. **Monitoring Coverage**
   - Ensure all critical paths have monitoring
   - Set up synthetic monitoring
   - Regular health check validation

2. **Testing**
   - Chaos engineering tests
   - Load testing
   - Dependency failure simulation

3. **Capacity Planning**
   - Monitor resource usage trends
   - Plan for peak loads
   - Auto-scaling configuration

4. **Security**
   - Regular security audits
   - API key rotation
   - Access control reviews

## Tools and Resources

- **Monitoring:** Grafana, Prometheus, Alertmanager
- **Logging:** ELK stack or similar
- **Tracing:** Jaeger
- **Incident Management:** PagerDuty
- **Communication:** Slack, Statuspage
- **Documentation:** This runbook, architecture docs

## Contact Information

- **On-call Engineer:** PagerDuty rotation
- **DevOps Team:** devops@company.com
- **Security Team:** security@company.com
- **Management:** management@company.com