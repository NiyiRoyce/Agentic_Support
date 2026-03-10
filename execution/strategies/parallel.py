# Execute tools in parallel
"""Parallel execution strategy"""
from typing import List, Optional
import asyncio
import logging

from execution.models import ToolCall, ToolResult, ToolStatus
from execution.core.context import ExecutionContext
from execution.core.registry import ToolRegistry
from execution.core.executor import ToolExecutor

logger = logging.getLogger(__name__)


class ParallelStrategy:
    """Execute tools concurrently"""
    
    def __init__(
        self,
        registry: ToolRegistry,
        executor: ToolExecutor,
        max_concurrent: int = 10,
    ):
        self.registry = registry
        self.executor = executor
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute(
        self,
        tool_calls: List[ToolCall],
        context: ExecutionContext,
    ) -> List[ToolResult]:
        """
        Execute tools in parallel
        
        Args:
            tool_calls: List of tool calls
            context: Execution context
            
        Returns:
            List of tool results (in original order)
        """
        logger.info(f"Executing {len(tool_calls)} tools in parallel")
        
        # Create tasks for all tool calls
        tasks = [
            self._execute_with_semaphore(tool_call, context, i)
            for i, tool_call in enumerate(tool_calls)
        ]
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Add all results to context
        for result in results:
            context.add_result(result)
        
        # Log summary
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Parallel execution complete: "
            f"{success_count}/{len(results)} succeeded"
        )
        
        return results
    
    async def _execute_with_semaphore(
        self,
        tool_call: ToolCall,
        context: ExecutionContext,
        index: int,
    ) -> ToolResult:
        """Execute single tool with semaphore control"""
        async with self.semaphore:
            tool = self.registry.get(tool_call.tool_name)
            
            if not tool:
                logger.error(f"Tool not found: {tool_call.tool_name}")
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    status=ToolStatus.FAILED,
                    error=f"Tool not found: {tool_call.tool_name}",
                    execution_time_ms=0,
                    metadata={"index": index},
                )
            
            logger.debug(f"Starting parallel execution of {tool_call.tool_name}")
            
            result = await self.executor.execute(
                tool=tool,
                params=tool_call.params,
                context=context,
            )
            
            result.metadata["index"] = index
            
            logger.debug(
                f"Completed {tool_call.tool_name}: "
                f"{'success' if result.success else 'failed'}"
            )
            
            return result