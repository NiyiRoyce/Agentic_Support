# ToolCall, ToolMetadata
"""Tool-related models"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from .status import ToolStatus


class ToolCategory(str, Enum):
    """Tool categories"""
    HELPDESK = "helpdesk"
    ECOMMERCE = "ecommerce"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"
    WORKFLOW = "workflow"


class ToolCall(BaseModel):
    """A single tool invocation request"""
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = 30
    retry_on_failure: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result from a tool execution"""
    tool_name: str
    status: ToolStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def success(self) -> bool:
        return self.status == ToolStatus.SUCCESS


class ToolMetadata(BaseModel):
    """Metadata about a tool"""
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    requires_auth: bool = True
    parameter_schema: Dict[str, Any]
    response_schema: Optional[Dict[str, Any]] = None
    rate_limit: Optional[int] = None  # Max calls per minute
    timeout_seconds: int = 30
    idempotent: bool = False
    tags: List[str] = Field(default_factory=list)