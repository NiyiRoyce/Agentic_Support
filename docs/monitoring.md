# Monitoring Guide

## Metrics

The application exposes Prometheus metrics at `/metrics`:

### HTTP Metrics
- `http_requests_total`: Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds`: Request duration histogram

### LLM Metrics
- `llm_requests_total`: Total LLM requests by provider and model
- `llm_tokens_total`: Token usage by provider, model, type (input/output)
- `llm_cost_total`: Total LLM costs in USD

### Agent Metrics
- `agent_executions_total`: Agent execution counts by type and result
- `agent_execution_duration_seconds`: Agent execution duration

### Memory Metrics
- `memory_operations_total`: Memory operations by type and store

## Logging

### Structured Logging
All logs are JSON-formatted with the following fields:
- `timestamp`: ISO format
- `level`: Log level
- `logger`: Logger name
- `message`: Log message
- Additional context fields

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Warning conditions
- `ERROR`: Error conditions
- `CRITICAL`: Critical errors

## Tracing

OpenTelemetry tracing is configured for distributed tracing.

### Setting up Jaeger/OTLP Collector

1. Run Jaeger:
```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest
```

2. Set `OTLP_ENDPOINT=http://localhost:14268/api/traces`

3. View traces at http://localhost:16686

## Alerting

### Recommended Alerts

1. **High Error Rate**
   - Metric: `http_requests_total{status_code=~"5.."} / http_requests_total`
   - Threshold: > 5% over 5 minutes
   - Action: Check application logs, restart if needed

2. **LLM Provider Failures**
   - Metric: `llm_requests_total` with failures
   - Threshold: > 10 failures per minute
   - Action: Check provider status, switch to fallback

3. **High Latency**
   - Metric: `http_request_duration_seconds{quantile="0.95"}`
   - Threshold: > 10 seconds
   - Action: Check resource usage, scale up

4. **Memory Issues**
   - Metric: System memory usage
   - Threshold: > 90%
   - Action: Restart or scale

### Alertmanager Configuration

```yaml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'slack'
  routes:
  - match:
      severity: critical
    receiver: 'pagerduty'

receivers:
- name: 'slack'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK'
    channel: '#alerts'
    title: '{{ .GroupLabels.alertname }}'
    text: '{{ .CommonAnnotations.description }}'
```

## Health Checks

### Application Health
- Endpoint: `GET /health`
- Returns: Basic uptime status

### Dependency Checks
- Redis connectivity
- Vector store availability
- LLM provider reachability

## Cost Monitoring

### LLM Costs
Monitor `llm_cost_total` metric for spending.

### Cost Optimization
1. Use cost-based routing strategy
2. Set up budgets and alerts
3. Monitor token usage patterns
4. Cache frequent queries

## Dashboards

### Grafana Dashboard

Import the provided dashboard JSON or create:

1. **Request Rate**: Requests per second by endpoint
2. **Error Rate**: 5xx errors over time
3. **Latency**: P95 response time
4. **LLM Usage**: Requests and costs by provider
5. **Agent Performance**: Success rates and durations

### Sample Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])

# LLM costs per hour
increase(llm_cost_total[1h])
```

## Troubleshooting

### Common Issues

1. **High Latency**
   - Check LLM provider response times
   - Monitor Redis performance
   - Review vector search queries

2. **Memory Leaks**
   - Monitor memory usage over time
   - Check for session cleanup
   - Review vector store size

3. **Provider Failures**
   - Check API key validity
   - Monitor provider status pages
   - Test fallback mechanisms

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG uvicorn app.main:app
```

Use `/docs` endpoint for API testing.