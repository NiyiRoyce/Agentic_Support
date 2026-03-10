# ExecutionError, ToolError
"""Error models for execution layer"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ToolError(Exception):
    """Base exception for tool execution errors"""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.params = params
        self.original_error = original_error
        self.error_code = error_code
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "tool_name": self.tool_name,
            "params": self.params,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "original_error": str(self.original_error) if self.original_error else None,
        }


class ValidationError(ToolError):
    """Parameter validation failed"""
    pass


class RateLimitError(ToolError):
    """Rate limit exceeded"""
    pass


class CircuitBreakerError(ToolError):
    """Circuit breaker is open"""
    pass


class TimeoutError(ToolError):
    """Execution timeout exceeded"""
    pass


class ExecutionError(BaseModel):
    """Structured error information"""
    message: str
    tool_name: Optional[str] = None
    error_code: Optional[str] = None
    error_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None
    recoverable: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }