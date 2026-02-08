# Conditional execution (if/else)
"""Conditional execution strategy"""
from typing import List, Dict, Any, Optional, Callable
import logging

from execution.models import ToolCall, ToolResult
from execution.core.context import ExecutionContext
from execution.core.registry import ToolRegistry
from execution.core.executor import ToolExecutor

logger = logging.getLogger(__name__)


class Condition:
    """Represents a conditional branch"""
    
    def __init__(
        self,
        condition: Callable[[ExecutionContext], bool],
        tool_calls: List[ToolCall],
        description: str = "",
    ):
        self.condition = condition
        self.tool_calls = tool_calls
        self.description = description
    
    def evaluate(self, context: ExecutionContext) -> bool:
        """Evaluate condition"""
        try:
            return self.condition(context)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return False


class ConditionalStrategy:
    """Execute tools based on conditions"""
    
    def __init__(
        self,
        registry: ToolRegistry,
        executor: ToolExecutor,
    ):
        self.registry = registry
        self.executor = executor
    
    async def execute_if_else(
        self,
        condition: Callable[[ExecutionContext], bool],
        if_true: List[ToolCall],
        if_false: List[ToolCall],
        context: ExecutionContext,
    ) -> List[ToolResult]:
        """
        Execute tools based on if/else condition
        
        Args:
            condition: Condition function
            if_true: Tools to execute if condition is true
            if_false: Tools to execute if condition is false
            context: Execution context
            
        Returns:
            List of tool results
        """
        try:
            should_execute_true = condition(context)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            should_execute_true = False
        
        tool_calls = if_true if should_execute_true else if_false
        branch = "true" if should_execute_true else "false"
        
        logger.info(
            f"Condition evaluated to {branch}, "
            f"executing {len(tool_calls)} tool(s)"
        )
        
        results = []
        for tool_call in tool_calls:
            tool = self.registry.get(tool_call.tool_name)
            if not tool:
                logger.error(f"Tool not found: {tool_call.tool_name}")
                continue
            
            result = await self.executor.execute(
                tool=tool,
                params=tool_call.params,
                context=context,
            )
            
            results.append(result)
            context.add_result(result)
        
        return results
    
    async def execute_switch(
        self,
        branches: List[Condition],
        default: Optional[List[ToolCall]] = None,
        context: ExecutionContext,
    ) -> List[ToolResult]:
        """
        Execute tools based on multiple conditions (switch-case)
        
        Args:
            branches: List of condition branches
            default: Default tools if no condition matches
            context: Execution context
            
        Returns:
            List of tool results
        """
        # Find first matching branch
        selected_branch = None
        for i, branch in enumerate(branches):
            if branch.evaluate(context):
                selected_branch = branch
                logger.info(
                    f"Branch {i} matched: {branch.description or 'unnamed'}"
                )
                break
        
        # Use default if no match
        if selected_branch is None:
            if default:
                logger.info("No branch matched, executing default")
                tool_calls = default
            else:
                logger.warning("No branch matched and no default provided")
                return []
        else:
            tool_calls = selected_branch.tool_calls
        
        # Execute selected tools
        results = []
        for tool_call in tool_calls:
            tool = self.registry.get(tool_call.tool_name)
            if not tool:
                logger.error(f"Tool not found: {tool_call.tool_name}")
                continue
            
            result = await self.executor.execute(
                tool=tool,
                params=tool_call.params,
                context=context,
            )
            
            results.append(result)
            context.add_result(result)
        
        return results
    
    @staticmethod
    def create_condition_from_result(
        tool_name: str,
        check: Callable[[ToolResult], bool],
    ) -> Callable[[ExecutionContext], bool]:
        """
        Create condition based on previous tool result
        
        Args:
            tool_name: Name of tool to check result for
            check: Function to evaluate result
            
        Returns:
            Condition function
        """
        def condition(context: ExecutionContext) -> bool:
            result = context.get_result(tool_name)
            if result is None:
                return False
            return check(result)
        
        return condition
    
    @staticmethod
    def create_condition_from_context(
        key: str,
        check: Callable[[Any], bool],
    ) -> Callable[[ExecutionContext], bool]:
        """
        Create condition based on context value
        
        Args:
            key: Context key to check
            check: Function to evaluate value
            
        Returns:
            Condition function
        """
        def condition(context: ExecutionContext) -> bool:
            value = context.get_context_value(key)
            if value is None:
                return False
            return check(value)
        
        return condition