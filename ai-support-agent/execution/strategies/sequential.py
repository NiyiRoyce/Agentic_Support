# Execute tools sequentially
"""Sequential execution strategy"""
from typing import List, Optional
import logging

from execution.models import ToolCall, ToolResult
from execution.core.context import ExecutionContext
from execution.core.registry import ToolRegistry
from execution.core.executor import ToolExecutor

logger = logging.getLogger(__name__)


class SequentialStrategy:
    """Execute tools one after another"""
    
    def __init__(
        self,
        registry: ToolRegistry,
        executor: ToolExecutor,
    ):
        self.registry = registry
        self.executor = executor
    
    async def execute(
        self,
        tool_calls: List[ToolCall],
        context: ExecutionContext,
        stop_on_error: bool = False,
        pass_results: bool = False,
    ) -> List[ToolResult]:
        """
        Execute tools sequentially
        
        Args:
            tool_calls: List of tool calls
            context: Execution context
            stop_on_error: Stop execution on first error
            pass_results: Pass previous result to next tool
            
        Returns:
            List of tool results
        """
        results = []
        
        for i, tool_call in enumerate(tool_calls):
            tool = self.registry.get(tool_call.tool_name)
            if not tool:
                logger.error(f"Tool not found: {tool_call.tool_name}")
                if stop_on_error:
                    break
                continue
            
            # Prepare parameters
            params = tool_call.params.copy()
            
            # Pass previous result if configured
            if pass_results and i > 0 and results:
                last_result = results[-1]
                if last_result.success and last_result.data:
                    params["_previous_result"] = last_result.data
                    logger.debug(
                        f"Passing result from {last_result.tool_name} "
                        f"to {tool_call.tool_name}"
                    )
            
            # Execute tool
            logger.info(
                f"Executing tool {i+1}/{len(tool_calls)}: {tool_call.tool_name}"
            )
            
            result = await self.executor.execute(
                tool=tool,
                params=params,
                context=context,
            )
            
            results.append(result)
            context.add_result(result)
            
            # Check for errors
            if not result.success:
                logger.warning(
                    f"Tool {tool_call.tool_name} failed: {result.error}"
                )
                if stop_on_error:
                    logger.info("Stopping execution due to error")
                    break
            else:
                logger.info(
                    f"Tool {tool_call.tool_name} succeeded "
                    f"({result.execution_time_ms:.2f}ms)"
                )
        
        return results