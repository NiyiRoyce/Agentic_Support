"""Prometheus metrics collection."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest


# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# LLM metrics
LLM_REQUEST_COUNT = Counter(
    "llm_requests_total", "Total number of LLM requests", ["provider", "model"]
)

LLM_TOKEN_COUNT = Counter(
    "llm_tokens_total",
    "Total number of tokens used",
    ["provider", "model", "type"],  # token types: input, output
)

LLM_COST = Counter("llm_cost_total", "Total LLM cost in USD", ["provider", "model"])

# Agent metrics
AGENT_EXECUTION_COUNT = Counter(
    "agent_executions_total",
    "Total number of agent executions",
    ["agent_type", "result"],
)

AGENT_EXECUTION_DURATION = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_type"],
)

# Memory metrics
MEMORY_OPERATION_COUNT = Counter(
    "memory_operations_total",
    "Total number of memory operations",
    ["operation", "store_type"],  # operation: save, load, delete
)

# System metrics
ACTIVE_CONNECTIONS = Gauge("active_connections", "Number of active connections")


def get_metrics() -> str:
    """
    Get current metrics in Prometheus format.

    Returns:
        Metrics as string
    """
    return generate_latest().decode("utf-8")


def increment_request_count(method: str, endpoint: str, status_code: int) -> None:
    """Increment HTTP request counter."""
    REQUEST_COUNT.labels(
        method=method, endpoint=endpoint, status_code=status_code
    ).inc()


def observe_request_duration(method: str, endpoint: str, duration: float) -> None:
    """Observe HTTP request duration."""
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def increment_llm_request_count(provider: str, model: str) -> None:
    """Increment LLM request counter."""
    LLM_REQUEST_COUNT.labels(provider=provider, model=model).inc()


def increment_llm_token_count(
    provider: str, model: str, token_type: str, count: int
) -> None:
    """Increment LLM token counter."""
    LLM_TOKEN_COUNT.labels(provider=provider, model=model, type=token_type).inc(count)


def increment_llm_cost(provider: str, model: str, cost: float) -> None:
    """Increment LLM cost counter."""
    LLM_COST.labels(provider=provider, model=model).inc(cost)


def increment_agent_execution_count(agent_type: str, result: str) -> None:
    """Increment agent execution counter."""
    AGENT_EXECUTION_COUNT.labels(agent_type=agent_type, result=result).inc()


def observe_agent_execution_duration(agent_type: str, duration: float) -> None:
    """Observe agent execution duration."""
    AGENT_EXECUTION_DURATION.labels(agent_type=agent_type).observe(duration)


def increment_memory_operation_count(operation: str, store_type: str) -> None:
    """Increment memory operation counter."""
    MEMORY_OPERATION_COUNT.labels(operation=operation, store_type=store_type).inc()


def set_active_connections(count: int) -> None:
    """Set active connections gauge."""
    ACTIVE_CONNECTIONS.set(count)
