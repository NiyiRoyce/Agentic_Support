# Timeout handling
"""Timeout handling for tool executions"""
import asyncio
from typing import Callable, Any, Optional, TypeVar
from datetime import datetime

from execution.models import TimeoutError as ExecutionTimeoutError

T = TypeVar('T')


class TimeoutHandler:
    """Handles execution timeouts"""
    
    def __init__(self, default_timeout_seconds: int = 30):
        self.default_timeout_seconds = default_timeout_seconds
        self._tool_timeouts: dict[str, int] = {}
    
    def configure(self, tool_name: str, timeout_seconds: int):
        """Configure timeout for specific tool"""
        self._tool_timeouts[tool_name] = timeout_seconds
    
    def get_timeout(self, tool_name: Optional[str] = None) -> int:
        """Get timeout for tool"""
        if tool_name and tool_name in self._tool_timeouts:
            return self._tool_timeouts[tool_name]
        return self.default_timeout_seconds
    
    async def execute_with_timeout(
        self,
        func: Callable[..., Any],
        *args,
        tool_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        **kwargs,
    ) -> T:
        """
        Execute function with timeout
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            tool_name: Tool name for timeout lookup
            timeout_seconds: Override timeout
            **kwargs: Keyword arguments
            
        Returns:
            Result from func
            
        Raises:
            ExecutionTimeoutError if timeout exceeded
        """
        timeout = timeout_seconds or self.get_timeout(tool_name)
        start_time = datetime.utcnow()
        
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout,
            )
            return result
            
        except asyncio.TimeoutError:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            raise ExecutionTimeoutError(
                message=f"Execution exceeded timeout of {timeout}s (elapsed: {elapsed:.2f}s)",
                tool_name=tool_name,
                error_code="TIMEOUT",
            )