# Low-level tool executor
"""Low-level tool executor with safety mechanisms"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from execution.tools.base import BaseTool
from execution.models import (
    ToolResult,
    ToolStatus,
    ToolError,
    ValidationError,
    CircuitBreakerError,
    RateLimitError,
)
from execution.core.context import ExecutionContext
from execution.safety import (
    CircuitBreaker,
    RetryStrategy,
    MultiRateLimiter,
    TimeoutHandler,
    ExecutionValidator,
)

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes individual tools with safety mechanisms"""
    
    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        retry_strategy: RetryStrategy,
        rate_limiter: MultiRateLimiter,
        timeout_handler: TimeoutHandler,
        validator: ExecutionValidator,
    ):
        self.circuit_breaker = circuit_breaker
        self.retry_strategy = retry_strategy
        self.rate_limiter = rate_limiter
        self.timeout_handler = timeout_handler
        self.validator = validator
    
    async def execute(
        self,
        tool: BaseTool,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        """
        Execute a tool with all safety mechanisms
        
        Args:
            tool: Tool to execute
            params: Tool parameters
            context: Execution context
            
        Returns:
            ToolResult
        """
        start_time = datetime.utcnow()
        tool_name = tool.name
        
        try:
            # 1. Validate parameters
            validation_result = await self.validator.validate_params(tool, params)
            if not validation_result.is_valid:
                raise ValidationError(
                    message=f"Parameter validation failed: {validation_result.errors}",
                    tool_name=tool_name,
                    params=params,
                    error_code="VALIDATION_ERROR",
                )
            
            # Log warnings
            if validation_result.warnings:
                logger.warning(
                    f"Tool {tool_name} validation warnings: {validation_result.warnings}"
                )
            
            # 2. Check circuit breaker
            can_execute = await self.circuit_breaker.can_execute(tool_name)
            if not can_execute:
                raise CircuitBreakerError(
                    message=f"Circuit breaker is open for tool: {tool_name}",
                    tool_name=tool_name,
                    params=params,
                    error_code="CIRCUIT_OPEN",
                )
            
            # 3. Check rate limit
            acquired = await self.rate_limiter.acquire(tool_name)
            if not acquired:
                raise RateLimitError(
                    message=f"Rate limit exceeded for tool: {tool_name}",
                    tool_name=tool_name,
                    params=params,
                    error_code="RATE_LIMITED",
                )
            
            # 4. Execute with retry and timeout
            result, attempt_count = await self.retry_strategy.execute_with_result(
                func=self._execute_with_timeout,
                tool=tool,
                params=params,
                context=context,
                tool_name=tool_name,
            )
            
            # Update result with retry count
            result.retry_count = attempt_count - 1
            
            # 5. Record success in circuit breaker
            await self.circuit_breaker.record_success(tool_name)
            
            # 6. Validate result if schema available
            if result.success and result.data:
                result_validation = await self.validator.validate_result(
                    tool, result.data
                )
                if not result_validation.is_valid:
                    logger.warning(
                        f"Tool {tool_name} result validation failed: "
                        f"{result_validation.errors}"
                    )
            
            return result
            
        except (ValidationError, CircuitBreakerError, RateLimitError) as e:
            # Non-retryable errors
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Map error types to status
            status = ToolStatus.FAILED
            if isinstance(e, CircuitBreakerError):
                status = ToolStatus.CIRCUIT_OPEN
            elif isinstance(e, RateLimitError):
                status = ToolStatus.RATE_LIMITED
            
            return ToolResult(
                tool_name=tool_name,
                status=status,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"error_code": e.error_code},
            )
            
        except Exception as e:
            # Unexpected errors
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Record failure in circuit breaker
            await self.circuit_breaker.record_failure(tool_name)
            
            logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
            
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"error_type": type(e).__name__},
            )
    
    async def _execute_with_timeout(
        self,
        tool: BaseTool,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        """Execute tool with timeout"""
        return await self.timeout_handler.execute_with_timeout(
            func=tool._execute_with_timing,
            params=params,
            context=context,
            tool_name=tool.name,
        )