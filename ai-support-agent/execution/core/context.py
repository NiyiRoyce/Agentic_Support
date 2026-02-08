# ExecutionContext (state, results, errors)
"""Execution context for tracking state"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from execution.models import (
    ToolResult,
    ExecutionError,
    ExecutionStatus,
)


class ExecutionContext:
    """Tracks execution state across tool calls"""
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        shared_context: Optional[Dict[str, Any]] = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.shared_context = shared_context or {}  # Shared data across tools
        
        self.results: List[ToolResult] = []
        self.errors: List[ExecutionError] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.status = ExecutionStatus.PENDING
        
        # Tool execution tracking
        self._tool_results: Dict[str, ToolResult] = {}
        self._execution_order: List[str] = []
    
    def add_result(self, result: ToolResult):
        """Add a tool result"""
        self.results.append(result)
        self._tool_results[result.tool_name] = result
        self._execution_order.append(result.tool_name)
    
    def add_error(self, error: ExecutionError):
        """Add an error"""
        self.errors.append(error)
    
    def get_result(self, tool_name: str) -> Optional[ToolResult]:
        """Get result from a specific tool"""
        return self._tool_results.get(tool_name)
    
    def get_last_result(self) -> Optional[ToolResult]:
        """Get the most recent result"""
        return self.results[-1] if self.results else None
    
    def set_context_value(self, key: str, value: Any):
        """Set a value in shared context"""
        self.shared_context[key] = value
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get a value from shared context"""
        return self.shared_context.get(key, default)
    
    def complete(self, status: ExecutionStatus):
        """Mark execution as complete"""
        self.status = status
        self.end_time = datetime.utcnow()
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get execution duration in milliseconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete"""
        return self.end_time is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "results": [r.model_dump() for r in self.results],
            "errors": [e.model_dump() for e in self.errors],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "execution_order": self._execution_order,
        }