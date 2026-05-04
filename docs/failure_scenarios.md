# Failure Scenarios & Recovery Runbooks

This document outlines common failure scenarios and recovery procedures for the AI Support Agent system.

## Table of Contents
1. [LLM Provider Failures](#llm-provider-failures)
2. [Memory Store Failures](#memory-store-failures)
3. [Knowledge Base Issues](#knowledge-base-issues)
4. [Circuit Breaker Trips](#circuit-breaker-trips)
5. [Cascade Failures](#cascade-failures)
6. [Performance Degradation](#performance-degradation)

---

## LLM Provider Failures

### Scenario: OpenAI API Timeout

**Symptoms:**
- Requests timing out after 30 seconds
- Error: `APITimeout: Request timed out`
- Increased latency in metrics
- Error rate spike on `/api/v1/chat` endpoint

**Root Causes:**
- OpenAI service degradation
- Network connectivity issues
- High volume of concurrent requests

**Immediate Response (1-5 minutes):**

```bash
# 1. Check OpenAI status
curl https://status.openai.com/api/v2/status.json | jq '.status.indicator'

# 2. Verify network connectivity
ping api.openai.com
traceroute api.openai.com

# 3. Monitor error rate
kubectl logs -f deployment/ai-support-agent | grep "APITimeout"

# 4. Check metrics
curl http://localhost:9090/api/v1/query?query=rate(llm_requests_total%7Bstatus%3D%22error%22%7D%5B5m%5D)
```

**Mitigation (5-15 minutes):**

```bash
# 1. Switch to Anthropic fallback provider
kubectl set env deployment/ai-support-agent \
  PRIMARY_LLM_PROVIDER=anthropic \
  FALLBACK_LLM_PROVIDER=openai

# 2. Reduce request concurrency
kubectl set env deployment/ai-support-agent \
  MAX_CONCURRENT_REQUESTS=10

# 3. Increase timeout threshold temporarily
kubectl set env deployment/ai-support-agent \
  LLM_REQUEST_TIMEOUT=60

# 4. Restart deployment to apply changes
kubectl rollout restart deployment/ai-support-agent

# 5. Monitor recovery
kubectl rollout status deployment/ai-support-agent
```

**Investigation (15-30 minutes):**

```bash
# 1. Check application logs for patterns
kubectl logs deployment/ai-support-agent --since=30m | \
  grep -E "APITimeout|error" | \
  tail -100

# 2. Analyze response times
kubectl logs deployment/ai-support-agent --since=30m | \
  jq 'select(.level=="info") | select(.duration_ms > 30000)'

# 3. Check API quota usage
curl -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  https://api.openai.com/v1/dashboard/billing/usage \
  -s | jq '.data[] | select(.timestamp > now-86400) | .usage'
```

**Recovery (15-60 minutes):**

```bash
# 1. Monitor fallback provider performance
while true; do
  curl -s http://localhost:9090/api/v1/query?query=rate(llm_requests_total%7Bstatus%3D%22success%22%7D%5B1m%5D) | \
  jq '.data.result[] | select(.metric.provider=="anthropic")'
  sleep 10
done

# 2. Once OpenAI recovers, verify latency is back to normal
# (Should return to < 5 seconds average)
kubectl logs deployment/ai-support-agent | \
  jq 'select(.provider=="openai") | .duration_ms' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "ms"}'

# 3. Switch back to OpenAI as primary
kubectl set env deployment/ai-support-agent \
  PRIMARY_LLM_PROVIDER=openai

# 4. Monitor for 5-10 minutes to confirm stability
kubectl top pods
```

### Scenario: LLM Provider Rate Limit

**Symptoms:**
- Error: `RateLimitError: Rate limit exceeded`
- HTTP 429 responses
- Sudden traffic spike in metrics

**Immediate Response (1-3 minutes):**

```bash
# 1. Acknowledge rate limit alert
kubectl get events | grep "rate.limit"

# 2. Check current request rate
curl http://localhost:9090/api/v1/query?query=rate\(llm_requests_total\[1m\]\)

# 3. Calculate requests per minute
kubectl logs deployment/ai-support-agent --since=1m | \
  grep "completed request" | wc -l
```

**Mitigation (3-10 minutes):**

```bash
# 1. Enable request queue with backpressure
kubectl patch deployment ai-support-agent \
  --type='json' -p='[
    {"op": "replace", "path": "/spec/template/spec/containers/0/env", 
     "value": [
       {"name": "ENABLE_REQUEST_QUEUE", "value": "true"},
       {"name": "MAX_QUEUE_SIZE", "value": "1000"},
       {"name": "QUEUE_DRAIN_RATE", "value": "10"}
     ]}
  ]'

# 2. Scale down replicas temporarily to reduce load
kubectl scale deployment/ai-support-agent --replicas=1

# 3. Monitor queue depth
watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=request_queue_depth | jq'
```

**Recovery (10-30 minutes):**

```bash
# 1. Once rate limit clears (monitor for 5 minutes)
# 2. Scale back to normal replicas
kubectl scale deployment/ai-support-agent --replicas=3

# 3. Increase rate limit quota if using paid tier
# (Contact OpenAI support)

# 4. Implement request batching to reduce API calls
# (Development task, not immediate recovery)
```

---

## Memory Store Failures

### Scenario: Redis Connection Loss

**Symptoms:**
- Error: `ConnectionError: Cannot connect to Redis`
- Session context unavailable
- Users getting different responses (loss of context)
- Error rate spike in `/api/v1/chat` endpoint

**Immediate Response (1-5 minutes):**

```bash
# 1. Check Redis pod status
kubectl get pods | grep redis
kubectl describe pod redis-0

# 2. Verify Redis is running
kubectl exec -it redis-0 -- redis-cli ping

# 3. Check connection logs
kubectl logs redis-0 --tail=50

# 4. Monitor application errors
kubectl logs deployment/ai-support-agent | grep "ConnectionError"
```

**Mitigation (5-10 minutes):**

```bash
# 1. If Redis pod is crashlooping, check logs
kubectl logs redis-0 --previous

# 2. Restart Redis pod
kubectl delete pod redis-0
# StatefulSet will auto-create new pod

# 3. Wait for pod to be ready
kubectl wait --for=condition=ready pod redis-0 --timeout=300s

# 4. Configure app to use in-memory fallback store
kubectl set env deployment/ai-support-agent \
  MEMORY_STORE=memory \
  FALLBACK_STORE=memory

# 5. Restart application pods
kubectl rollout restart deployment/ai-support-agent
```

**Recovery (10-20 minutes):**

```bash
# 1. Once Redis is healthy
kubectl exec -it redis-0 -- redis-cli info stats

# 2. Verify connection
redis-cli -h redis-0.redis.default.svc.cluster.local ping

# 3. Restore connection to Redis backend
kubectl set env deployment/ai-support-agent \
  MEMORY_STORE=redis \
  FALLBACK_STORE=memory

# 4. Restart app
kubectl rollout restart deployment/ai-support-agent

# 5. Validate sessions are persisting
kubectl logs deployment/ai-support-agent | grep "session.*saved"
```

### Scenario: Memory Store Disk Full

**Symptoms:**
- Error: `RuntimeError: No space left on device`
- Redis becoming unresponsive
- Increasing request latency
- Percentage disk usage near 100%

**Immediate Response (1-5 minutes):**

```bash
# 1. Check Redis storage usage
kubectl exec redis-0 -- du -sh /data/

# 2. Check available disk space
kubectl exec redis-0 -- df -h

# 3. Check Redis memory usage
kubectl exec -it redis-0 -- redis-cli info memory
```

**Mitigation (5-15 minutes):**

```bash
# 1. Reduce Redis TTL for sessions
kubectl exec -it redis-0 -- redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 2. Clear old sessions
kubectl exec -it redis-0 -- redis-cli EVAL \
  "return redis.call('del', unpack(redis.call('keys','session:*')))" 0

# 3. Verify space freed
kubectl exec redis-0 -- df -h

# 4. If space still critical, scale up PVC
kubectl patch pvc redis-storage -p \
  '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
```

---

## Knowledge Base Issues

### Scenario: Vector Store Unavailable

**Symptoms:**
- Error: `ChromaDB connection refused`
- Knowledge retrieval failing
- Agents unable to access documents
- Error rate spike in knowledge-dependent agents

**Immediate Response (1-5 minutes):**

```bash
# 1. Check ChromaDB pod
kubectl get pods -l app=chroma
kubectl describe pod chroma-0

# 2. Check ChromaDB logs
kubectl logs chroma-0 --tail=50

# 3. Verify vector store connectivity
kubectl exec -it chroma-0 -- \
  curl -s http://localhost:8000/api/v1/heartbeat

# 4. Check database file size
kubectl exec chroma-0 -- du -sh /data/
```

**Mitigation (5-15 minutes):**

```bash
# 1. Restart ChromaDB pod
kubectl delete pod chroma-0

# 2. Enable fallback to cached embeddings
kubectl set env deployment/ai-support-agent \
  RAG_FALLBACK_MODE=cached

# 3. Restart app to pick up config
kubectl rollout restart deployment/ai-support-agent

# 4. Monitor knowledge agent errors
kubectl logs deployment/ai-support-agent | \
  grep -E "knowledge|ChromaDB"
```

**Recovery (15-30 minutes):**

```bash
# 1. Once ChromaDB is healthy
kubectl exec -it chroma-0 -- \
  curl -s http://localhost:8000/api/v1/collections | \
  jq '.ids | length'

# 2. Verify embeddings are intact
kubectl exec -it chroma-0 -- \
  curl -s http://localhost:8000/api/v1/collections | \
  jq '.ids[0]'

# 3. Rebuild vector index if corrupted
python scripts/rebuild_index.py --docs-path=./docs

# 4. Disable fallback mode
kubectl set env deployment/ai-support-agent \
  RAG_FALLBACK_MODE=auto

# 5. Verify knowledge retrieval works
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are your operating hours?"}'
```

---

## Circuit Breaker Trips

### Scenario: Circuit Breaker Opens for External Service

**Symptoms:**
- Error: `CircuitBreakerOpen: Circuit breaker is OPEN`
- External service calls being rejected immediately
- Metrics show repeated failures from specific service

**Immediate Response (1-2 minutes):**

```bash
# 1. Identify which circuit breaker tripped
kubectl logs deployment/ai-support-agent | \
  grep "Circuit breaker" | \
  grep "opened"

# 2. Check service status
# e.g., for Shopify Orders service:
curl -s https://status.shopify.com/api/v2/status.json | \
  jq '.status.description'

# 3. Check metrics for the failed service
curl http://localhost:9090/api/v1/query?query=circuit_breaker_state | \
  jq '.data.result[] | select(.labels.status=="open")'
```

**Mitigation (2-5 minutes):**

```bash
# 1. Check external service health manually
curl -f https://api.shopify.com/admin/api/2024-01/graphql.json -H "X-Shopify-Access-Token: test" || true

# 2. If service is back online, reset circuit breaker
kubectl port-forward deployment/ai-support-agent 8000:8000 &
curl -X POST http://localhost:8000/admin/circuit-breaker/reset \
  -H "X-API-Key: ${ADMIN_API_KEY}" \
  -d '{"service": "shopify_orders"}'

# 3. Verify circuit breaker is closed
kubectl logs deployment/ai-support-agent | grep "closed"
```

---

## Cascade Failures

### Scenario: Multiple Systems Failing (Cascade)

**Symptoms:**
- Multiple error types appearing together
- System becoming unresponsive
- Cascading errors in logs
- All endpoints returning 5xx

**Immediate Response (1-3 minutes):**

```bash
# 1. Check overall system health
kubectl get nodes
kubectl top nodes
kubectl top pods

# 2. Check all critical services
kubectl get pods -A | grep -E "ai-support|redis|chroma"

# 3. Review error logs
kubectl logs deployment/ai-support-agent -f | \
  tail -100
```

**Emergency Mitigation (3-5 minutes):**

```bash
# 1. Scale down to single replica
kubectl scale deployment/ai-support-agent --replicas=1

# 2. Scale down other services to free resources
kubectl scale deployment/knowledge-agent --replicas=1

# 3. Check resources
kubectl describe node

# 4. If node is memory-constrained
# Option A: Delete non-essential pods
kubectl delete pod <non-essential-pod>

# Option B: Add more nodes
kubectl scale nodes <node-pool> --num-nodes=5

# 5. Once stable, gradually scale back up
kubectl scale deployment/ai-support-agent --replicas=2
sleep 60  # Wait and observe
kubectl scale deployment/ai-support-agent --replicas=3
```

**Recovery (15-30 minutes):**

```bash
# 1. Root cause analysis (after stabilization)
# Check logs for initial failure
kubectl logs deployment/ai-support-agent --since=30m | \
  head -100

# 2. Look for resource exhaustion
kubectl top nodes
kubectl top pods --all-namespaces --sort-by=memory

# 3. Check for memory leaks
# (Compare memory usage before/after restart)

# 4. Implement safeguards if resource issue:
# - Increase resource limits
# - Implement memory caching for LLM responses
# - Reduce session retention

# 5. Document incident
# See: docs/incident_response.md
```

---

## Performance Degradation

### Scenario: High Latency (P2 Incident)

**Symptoms:**
- Response times increased to 10-30 seconds
- 95th percentile latency exceeds threshold
- No errors, but slow responses
- User complaints about slowness

**Immediate Response (1-5 minutes):**

```bash
# 1. Check latency metrics
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket%5B5m%5D))'

# 2. Identify slow endpoints
kubectl logs deployment/ai-support-agent | \
  jq 'select(.duration_ms > 5000)' | \
  head -20

# 3. Check resource utilization
kubectl top pods --containers
kubectl top nodes
```

**Investigation (5-15 minutes):**

```bash
# 1. Check if specific agent is slow
kubectl logs deployment/ai-support-agent | \
  jq '.agent_type' | sort | uniq -c | sort -rn

# 2. Check LLM response times
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(llm_request_duration_seconds_bucket%5B5m%5D))'

# 3. Check database query times
kubectl logs deployment/ai-support-agent | \
  jq 'select(.component=="redis") | .duration_ms' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count}'

# 4. Check vector search times
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(rag_search_duration_seconds_bucket%5B5m%5D))'
```

**Optimization (15-30 minutes):**

```bash
# 1. If LLM is slow:
# - Switch to faster model (e.g., gpt-4o-mini)
# - Reduce max_tokens
# - Increase temperature for less computation

# 2. If database is slow:
# - Increase Redis memory buffer
# - Enable read replicas

# 3. If vector search is slow:
# - Reduce RAG search results (max_results=5 instead of 10)
# - Implement approximate nearest neighbor search

# 4. General optimization:
# - Scale replicas: kubectl scale deployment/ai-support-agent --replicas=5
# - Enable caching for responses
# - Implement request batching
```

---

## Post-Incident Actions

After resolving any incident:

1. **Document**: Update this runbook with any new learnings
2. **Alert**: Review alerting thresholds
3. **Monitoring**: Ensure metrics captured the issue
4. **Prevention**: Implement fixes to prevent recurrence
5. **Retrospective**: Schedule team discussion (for P0/P1 incidents)
