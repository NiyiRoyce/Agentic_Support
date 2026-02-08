# gorgias integration
"""Gorgias helpdesk tools"""
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import logging

from execution.tools.base import BaseTool
from execution.models import ToolResult, ToolStatus, ToolCategory
from execution.core.context import ExecutionContext

logger = logging.getLogger(__name__)


class GorgiasCreateTicketTool(BaseTool):
    """Create a ticket in Gorgias"""
    
    def __init__(self):
        super().__init__(
            name="gorgias_create_ticket",
            description="Create a support ticket in Gorgias helpdesk",
            category=ToolCategory.HELPDESK,
            requires_auth=True,
            timeout_seconds=30,
            idempotent=False,
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        start_time = datetime.utcnow()
        
        try:
            domain = params["domain"]
            api_key = params["api_key"]
            
            # Prepare ticket data
            ticket_data = {
                "messages": [
                    {
                        "channel": "email",
                        "via": "api",
                        "from_agent": False,
                        "body_text": params["message"],
                        "body_html": params.get("message_html", params["message"]),
                    }
                ],
                "customer": {
                    "email": params["customer_email"],
                    "name": params.get("customer_name"),
                },
                "channel": params.get("channel", "email"),
                "via": "api",
                "subject": params.get("subject", "Support Request"),
            }
            
            # Add tags if provided
            if "tags" in params:
                ticket_data["tags"] = params["tags"]
            
            # Add priority if provided
            if "priority" in params:
                ticket_data["priority"] = params["priority"]
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{domain}.gorgias.com/api/tickets",
                    json=ticket_data,
                    auth=(api_key, ""),
                    timeout=30.0,
                )
                response.raise_for_status()
                
                ticket = response.json()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "ticket": ticket,
                    "ticket_id": ticket.get("id"),
                    "ticket_url": ticket.get("uri"),
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to create Gorgias ticket: {e}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Gorgias subdomain",
                },
                "api_key": {
                    "type": "string",
                    "description": "Gorgias API key",
                },
                "customer_email": {
                    "type": "string",
                    "format": "email",
                    "description": "Customer email address",
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer name",
                },
                "subject": {
                    "type": "string",
                    "description": "Ticket subject",
                },
                "message": {
                    "type": "string",
                    "description": "Ticket message (plain text)",
                },
                "message_html": {
                    "type": "string",
                    "description": "Ticket message (HTML)",
                },
                "channel": {
                    "type": "string",
                    "enum": ["email", "chat", "phone", "facebook", "twitter"],
                    "default": "email",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ticket tags",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Ticket priority",
                },
            },
            "required": ["domain", "api_key", "customer_email", "message"],
        }


class GorgiasUpdateTicketTool(BaseTool):
    """Update a Gorgias ticket"""
    
    def __init__(self):
        super().__init__(
            name="gorgias_update_ticket",
            description="Update an existing Gorgias ticket",
            category=ToolCategory.HELPDESK,
            requires_auth=True,
            timeout_seconds=30,
            idempotent=False,
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        start_time = datetime.utcnow()
        
        try:
            domain = params["domain"]
            api_key = params["api_key"]
            ticket_id = params["ticket_id"]
            
            # Prepare update data
            update_data = {}
            
            if "status" in params:
                update_data["status"] = params["status"]
            
            if "priority" in params:
                update_data["priority"] = params["priority"]
            
            if "assignee_user_id" in params:
                update_data["assignee_user"] = {"id": params["assignee_user_id"]}
            
            if "tags" in params:
                update_data["tags"] = params["tags"]
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"https://{domain}.gorgias.com/api/tickets/{ticket_id}",
                    json=update_data,
                    auth=(api_key, ""),
                    timeout=30.0,
                )
                response.raise_for_status()
                
                ticket = response.json()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "ticket": ticket,
                    "ticket_id": ticket.get("id"),
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to update Gorgias ticket: {e}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "api_key": {"type": "string"},
                "ticket_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["open", "closed", "pending"],
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                },
                "assignee_user_id": {
                    "type": "integer",
                    "description": "User ID to assign ticket to",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["domain", "api_key", "ticket_id"],
        }


class GorgiasAddMessageTool(BaseTool):
    """Add a message to a Gorgias ticket"""
    
    def __init__(self):
        super().__init__(
            name="gorgias_add_message",
            description="Add a message/reply to an existing Gorgias ticket",
            category=ToolCategory.HELPDESK,
            requires_auth=True,
            timeout_seconds=30,
            idempotent=False,
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        start_time = datetime.utcnow()
        
        try:
            domain = params["domain"]
            api_key = params["api_key"]
            ticket_id = params["ticket_id"]
            
            # Prepare message data
            message_data = {
                "channel": params.get("channel", "email"),
                "via": "api",
                "from_agent": params.get("from_agent", True),
                "body_text": params["message"],
                "body_html": params.get("message_html", params["message"]),
            }
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{domain}.gorgias.com/api/tickets/{ticket_id}/messages",
                    json=message_data,
                    auth=(api_key, ""),
                    timeout=30.0,
                )
                response.raise_for_status()
                
                message = response.json()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "message": message,
                    "message_id": message.get("id"),
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to add message to Gorgias ticket: {e}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "api_key": {"type": "string"},
                "ticket_id": {"type": "string"},
                "message": {"type": "string"},
                "message_html": {"type": "string"},
                "channel": {
                    "type": "string",
                    "enum": ["email", "chat", "phone"],
                    "default": "email",
                },
                "from_agent": {
                    "type": "boolean",
                    "default": True,
                },
            },
            "required": ["domain", "api_key", "ticket_id", "message"],
        }