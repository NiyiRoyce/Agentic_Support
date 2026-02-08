# mock helpdesk (for testing)
"""Mock helpdesk tool for testing"""
from typing import Dict, Any, Optional
from datetime import datetime
import random
import logging

from execution.tools.base import BaseTool
from execution.models import ToolResult, ToolStatus, ToolCategory
from execution.core.context import ExecutionContext

logger = logging.getLogger(__name__)


class MockHelpdeskTool(BaseTool):
    """Mock helpdesk tool for testing without external dependencies"""
    
    def __init__(self):
        super().__init__(
            name="mock_helpdesk_create_ticket",
            description="Mock tool for creating support tickets (testing only)",
            category=ToolCategory.HELPDESK,
            requires_auth=False,
            timeout_seconds=5,
            idempotent=False,
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        start_time = datetime.utcnow()
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Generate mock ticket
        ticket_id = f"MOCK-{random.randint(1000, 9999)}"
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ToolResult(
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data={
                "ticket_id": ticket_id,
                "status": "open",
                "subject": params.get("subject", "Support Request"),
                "customer_email": params.get("customer_email"),
                "created_at": datetime.utcnow().isoformat(),
            },
            execution_time_ms=execution_time,
        )
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "customer_email": {
                    "type": "string",
                    "format": "email",
                },
                "subject": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["customer_email", "message"],
        }