# ToolResult, ExecutionResult models
"""Result aggregation and processing"""
from typing import List, Optional
from datetime import datetime

from execution.models import (
    ExecutionStatus,
    ToolResult,
    ToolStatus,
    ExecutionError,
    ExecutionResponse,
)


class ResultAggregator:
    """Aggregates tool results into execution response"""
    
    @staticmethod
    def aggregate(
        request_id: str,
        results: List[ToolResult],
        errors: List[ExecutionError],
        start_time: datetime,
        end_time: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> ExecutionResponse:
        """Aggregate results into response"""
        
        if end_time is None:
            end_time = datetime.utcnow()
        
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Determine overall status
        status = ResultAggregator._determine_status(results, errors)
        
        return ExecutionResponse(
            request_id=request_id,
            status=status,
            results=results,
            errors=errors,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
    
    @staticmethod
    def _determine_status(
        results: List[ToolResult],
        errors: List[ExecutionError],
    ) -> ExecutionStatus:
        """Determine overall execution status"""
        
        if not results and not errors:
            return ExecutionStatus.PENDING
        
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == ToolStatus.FAILED)
        timeout_count = sum(1 for r in results if r.status == ToolStatus.TIMEOUT)
        
        total_count = len(results)
        
        # All succeeded
        if success_count == total_count and total_count > 0:
            return ExecutionStatus.SUCCESS
        
        # All failed
        if failed_count == total_count or (failed_count + timeout_count) == total_count:
            return ExecutionStatus.FAILED
        
        # Any timeouts
        if timeout_count > 0:
            return ExecutionStatus.TIMEOUT
        
        # Some succeeded, some failed
        if success_count > 0 and failed_count > 0:
            return ExecutionStatus.PARTIAL
        
        return ExecutionStatus.FAILED