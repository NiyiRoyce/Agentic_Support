# Main execution dispatcher (executes plans)
"""Main execution dispatcher"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import logging
import uuid

from execution.core.registry import ToolRegistry
from execution.core.executor import ToolExecutor
from execution.core.context import ExecutionContext
from execution.core.result import ResultAggregator
from execution.models import (
    ExecutionRequest,
    ExecutionResponse,
    ExecutionPlan,
    ToolCall,
    ToolResult,
    ExecutionStatus,
    ExecutionMode,
    ExecutionError,
    ToolError,
)
from execution.safety import (
    CircuitBreaker,
    RetryStrategy,
    MultiRateLimiter,
    TimeoutHandler,
    ExecutionValidator,
)

logger = logging.getLogger(__name__)


class ExecutionDispatcher:
    """
    Main dispatcher for executing tools
    Coordinates between registry, executor, and strategies
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_strategy: Optional[RetryStrategy] = None,
        rate_limiter: Optional[MultiRateLimiter] = None,
        timeout_handler: Optional[TimeoutHandler] = None,
        validator: Optional[ExecutionValidator] = None,
        max_concurrent: int = 10,
    ):
        self.registry = registry
        
        # Initialize safety components
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.rate_limiter = rate_limiter or MultiRateLimiter()
        self.timeout_handler = timeout_handler or TimeoutHandler()
        self.validator = validator or ExecutionValidator()
        
        # Executor
        self.executor = ToolExecutor(
            circuit_breaker=self.circuit_breaker,
            retry_strategy=self.retry_strategy,
            rate_limiter=self.rate_limiter,
            timeout_handler=self.timeout_handler,
            validator=self.validator,
        )
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def dispatch(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResponse:
        """
        Dispatch execution request
        
        Args:
            request: Execution request
            
        Returns:
            Execution response
        """
        # Generate request ID if not provided
        request_id = request.request_id or str(uuid.uuid4())
        
        # Create execution context
        context = ExecutionContext(
            request_id=request_id,
            user_id=request.user_id,
            session_id=request.session_id,
            metadata=request.metadata,
            shared_context=request.context,
        )
        
        logger.info(
            f"Starting execution {request_id}: "
            f"{len(request.tool_calls)} tool(s), mode={request.execution_mode.value}"
        )
        
        try:
            # Validate tool calls
            validation_errors = self.registry.validate_tool_calls(
                [call.model_dump() for call in request.tool_calls]
            )
            if validation_errors:
                logger.error(f"Tool call validation failed: {validation_errors}")
                context.complete(ExecutionStatus.FAILED)
                return ResultAggregator.aggregate(
                    request_id=request_id,
                    results=[],
                    errors=[
                        ExecutionError(
                            message=error,
                            error_type="ValidationError",
                            error_code="INVALID_TOOL_CALL",
                        )
                        for error in validation_errors
                    ],
                    start_time=context.start_time,
                    end_time=datetime.utcnow(),
                    metadata=request.metadata,
                )
            
            # Execute based on mode
            if request.execution_mode == ExecutionMode.SEQUENTIAL:
                results = await self._execute_sequential(
                    tool_calls=request.tool_calls,
                    context=context,
                    stop_on_error=request.stop_on_error,
                )
            elif request.execution_mode == ExecutionMode.PARALLEL:
                results = await self._execute_parallel(
                    tool_calls=request.tool_calls,
                    context=context,
                )
            else:
                raise ValueError(f"Unsupported execution mode: {request.execution_mode}")
            
            # Determine final status
            if all(r.success for r in results):
                context.complete(ExecutionStatus.SUCCESS)
            elif any(r.success for r in results):
                context.complete(ExecutionStatus.PARTIAL)
            else:
                context.complete(ExecutionStatus.FAILED)
            
            logger.info(
                f"Completed execution {request_id}: "
                f"status={context.status.value}, "
                f"duration={context.duration_ms:.2f}ms"
            )
            
            # Aggregate results
            return ResultAggregator.aggregate(
                request_id=request_id,
                results=results,
                errors=context.errors,
                start_time=context.start_time,
                end_time=context.end_time,
                metadata=request.metadata,
            )
            
        except Exception as e:
            logger.error(f"Execution {request_id} failed: {e}", exc_info=True)
            context.complete(ExecutionStatus.FAILED)
            
            return ResultAggregator.aggregate(
                request_id=request_id,
                results=context.results,
                errors=[
                    ExecutionError(
                        message=str(e),
                        error_type=type(e).__name__,
                        error_code="EXECUTION_ERROR",
                    )
                ],
                start_time=context.start_time,
                end_time=datetime.utcnow(),
                metadata=request.metadata,
            )
    
    async def dispatch_plan(
        self,
        plan: ExecutionPlan,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> ExecutionResponse:
        """
        Dispatch execution plan from orchestration layer
        
        Args:
            plan: Execution plan
            user_id: User ID
            session_id: Session ID
            
        Returns:
            Execution response
        """
        request = ExecutionRequest(
            request_id=plan.plan_id,
            user_id=user_id,
            session_id=session_id,
            tool_calls=plan.tool_calls,
            execution_mode=plan.execution_mode,
            metadata=plan.metadata,
        )
        
        return await self.dispatch(request)
    
    async def _execute_sequential(
        self,
        tool_calls: List[ToolCall],
        context: ExecutionContext,
        stop_on_error: bool = False,
    ) -> List[ToolResult]:
        """Execute tools sequentially"""
        results = []
        
        for i, tool_call in enumerate(tool_calls):
            tool = self.registry.get(tool_call.tool_name)
            if not tool:
                error = ExecutionError(
                    message=f"Tool not found: {tool_call.tool_name}",
                    tool_name=tool_call.tool_name,
                    error_type="ToolNotFoundError",
                    error_code="TOOL_NOT_FOUND",
                )
                context.add_error(error)
                if stop_on_error:
                    break
                continue
            
            logger.debug(
                f"Executing tool {i+1}/{len(tool_calls)}: {tool_call.tool_name}"
            )
            
            result = await self.executor.execute(
                tool=tool,
                params=tool_call.params,
                context=context,
            )
            
            context.add_result(result)
            results.append(result)
            
            # Stop on error if configured
            if stop_on_error and not result.success:
                logger.warning(
                    f"Stopping execution after failed tool: {tool_call.tool_name}"
                )
                break
        
        return results
    
    async def _execute_parallel(
        self,
        tool_calls: List[ToolCall],
        context: ExecutionContext,
    ) -> List[ToolResult]:
        """Execute tools in parallel"""
        
        async def execute_single(tool_call: ToolCall) -> ToolResult:
            """Execute single tool with semaphore"""
            async with self.semaphore:
                tool = self.registry.get(tool_call.tool_name)
                if not tool:
                    error = ExecutionError(
                        message=f"Tool not found: {tool_call.tool_name}",
                        tool_name=tool_call.tool_name,
                        error_type="ToolNotFoundError",
                        error_code="TOOL_NOT_FOUND",
                    )
                    context.add_error(error)
                    # Return failed result
                    return ToolResult(
                        tool_name=tool_call.tool_name,
                        status="failed",
                        error=error.message,
                        execution_time_ms=0,
                    )
                
                return await self.executor.execute(
                    tool=tool,
                    params=tool_call.params,
                    context=context,
                )
        
        # Execute all tools concurrently
        tasks = [execute_single(call) for call in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Add all results to context
        for result in results:
            context.add_result(result)
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get dispatcher status"""
        return {
            "registry": self.registry.get_statistics(),
            "circuit_breakers": self.circuit_breaker.get_status(),
            "rate_limiters": self.rate_limiter.get_status(),
        }