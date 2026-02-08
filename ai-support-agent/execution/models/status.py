# ExecutionStatus enum
"""Execution status enums and states"""
from enum import Enum


class ExecutionStatus(str, Enum):
    """Overall execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ToolStatus(str, Enum):
    """Individual tool execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"


class ExecutionMode(str, Enum):
    """Execution strategy mode"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    COMPENSATING = "compensating"