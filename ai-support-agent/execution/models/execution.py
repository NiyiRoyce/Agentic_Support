# ExecutionRequest, ExecutionResponse
"""Execution request and response models"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .tool import ToolCall, ToolResult
from .status import ExecutionStatus, ExecutionMode
from .errors import ExecutionError


class ExecutionRequest(BaseModel):
    """Request to execute tools"""
    request_id: Optional[str] = None
    user_id: str
    session_id: Optional[str] = None
    tool_calls: List[ToolCall]
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    stop_on_error: bool = False
    timeout_seconds: Optional[int] = 300
    metadata: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)  # Shared context across tools


class ExecutionResponse(BaseModel):
    """Response from execution"""
    request_id: str
    status: ExecutionStatus
    results: List[ToolResult]
    errors: List[ExecutionError] = Field(default_factory=list)
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
    
    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)
    
    @property
    def failure_count(self) -> int:
        return len(self.errors)


class ExecutionPlan(BaseModel):
    """Structured execution plan from orchestration layer"""
    plan_id: str
    description: str
    tool_calls: List[ToolCall]
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)  # tool_name -> [dependent_tool_names]
    rollback_on_failure: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)