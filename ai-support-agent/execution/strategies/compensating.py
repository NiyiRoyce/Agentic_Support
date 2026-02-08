# Compensating transactions (rollback)
"""Compensating transaction strategy (Saga pattern)"""
from typing import List, Dict, Optional, Callable, Any
import logging

from execution.models import ToolCall, ToolResult
from execution.core.context import ExecutionContext
from execution.core.registry import ToolRegistry
from execution.core.executor import ToolExecutor

logger = logging.getLogger(__name__)


class CompensatingAction:
    """Represents a compensating action for rollback"""
    
    def __init__(
        self,
        tool_name: str,
        params: Dict[str, Any],
        description: str = "",
    ):
        self.tool_name = tool_name
        self.params = params
        self.description = description


class TransactionStep:
    """Represents a step in a saga transaction"""
    
    def __init__(
        self,
        forward: ToolCall,
        compensate: Optional[CompensatingAction] = None,
    ):
        self.forward = forward
        self.compensate = compensate


class CompensatingStrategy:
    """
    Execute tools with compensation support (Saga pattern)
    If any step fails, compensating actions are executed in reverse order
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        executor: ToolExecutor,
    ):
        self.registry = registry
        self.executor = executor
    
    async def execute(
        self,
        steps: List[TransactionStep],
        context: ExecutionContext,
    ) -> List[ToolResult]:
        """
        Execute transaction with compensation
        
        Args:
            steps: List of transaction steps
            context: Execution context
            
        Returns:
            List of tool results
        """
        results = []
        executed_steps = []
        
        logger.info(f"Starting compensating transaction with {len(steps)} steps")
        
        # Execute forward steps
        for i, step in enumerate(steps):
            tool = self.registry.get(step.forward.tool_name)
            if not tool:
                logger.error(f"Tool not found: {step.forward.tool_name}")
                # Trigger rollback
                await self._rollback(executed_steps, context)
                break
            
            logger.info(
                f"Executing step {i+1}/{len(steps)}: {step.forward.tool_name}"
            )
            
            result = await self.executor.execute(
                tool=tool,
                params=step.forward.params,
                context=context,
            )
            
            results.append(result)
            context.add_result(result)
            
            if not result.success:
                logger.error(
                    f"Step {i+1} failed: {step.forward.tool_name}. "
                    f"Initiating rollback..."
                )
                # Trigger rollback
                await self._rollback(executed_steps, context)
                break
            
            # Track successful step for potential rollback
            executed_steps.append((step, result))
            logger.info(f"Step {i+1} completed successfully")
        
        else:
            # All steps succeeded
            logger.info("All transaction steps completed successfully")
        
        return results
    
    async def _rollback(
        self,
        executed_steps: List[tuple[TransactionStep, ToolResult]],
        context: ExecutionContext,
    ):
        """
        Execute compensating actions in reverse order
        
        Args:
            executed_steps: Steps that were executed successfully
            context: Execution context
        """
        if not executed_steps:
            logger.info("No steps to rollback")
            return
        
        logger.warning(
            f"Rolling back {len(executed_steps)} step(s) "
            f"with compensating actions"
        )
        
        # Execute compensations in reverse order
        for step, forward_result in reversed(executed_steps):
            if step.compensate is None:
                logger.warning(
                    f"No compensating action for {step.forward.tool_name}, skipping"
                )
                continue
            
            tool = self.registry.get(step.compensate.tool_name)
            if not tool:
                logger.error(
                    f"Compensating tool not found: {step.compensate.tool_name}"
                )
                continue
            
            logger.info(
                f"Executing compensating action: {step.compensate.tool_name} "
                f"for {step.forward.tool_name}"
            )
            
            # Prepare compensation params (may use forward result)
            params = step.compensate.params.copy()
            if forward_result.data:
                params["_forward_result"] = forward_result.data
            
            try:
                result = await self.executor.execute(
                    tool=tool,
                    params=params,
                    context=context,
                )
                
                if result.success:
                    logger.info(
                        f"Compensation succeeded for {step.forward.tool_name}"
                    )
                else:
                    logger.error(
                        f"Compensation failed for {step.forward.tool_name}: "
                        f"{result.error}"
                    )
                
                context.add_result(result)
                
            except Exception as e:
                logger.error(
                    f"Compensation execution failed for {step.forward.tool_name}: {e}",
                    exc_info=True,
                )
        
        logger.info("Rollback completed")