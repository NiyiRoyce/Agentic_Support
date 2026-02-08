# slack notifier
"""Slack notification tool"""
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import logging

from execution.tools.base import BaseTool
from execution.models import ToolResult, ToolStatus, ToolCategory
from execution.core.context import ExecutionContext

logger = logging.getLogger(__name__)


class SlackNotificationTool(BaseTool):
    """Send notifications to Slack"""
    
    def __init__(self):
        super().__init__(
            name="slack_send_message",
            description="Send a message to a Slack channel",
            category=ToolCategory.NOTIFICATION,
            requires_auth=True,
            timeout_seconds=10,
            idempotent=False,
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        start_time = datetime.utcnow()
        
        try:
            webhook_url = params.get("webhook_url")
            token = params.get("token")
            
            # Prepare message
            message = {
                "text": params["message"],
            }
            
            # Add channel if specified
            if "channel" in params:
                message["channel"] = params["channel"]
            
            # Add blocks for rich formatting if provided
            if "blocks" in params:
                message["blocks"] = params["blocks"]
            
            # Add thread_ts for threading if provided
            if "thread_ts" in params:
                message["thread_ts"] = params["thread_ts"]
            
            async with httpx.AsyncClient() as client:
                if webhook_url:
                    # Use webhook URL
                    response = await client.post(
                        webhook_url,
                        json=message,
                        timeout=10.0,
                    )
                elif token:
                    # Use API token
                    response = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        json=message,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0,
                    )
                else:
                    raise ValueError("Either webhook_url or token must be provided")
                
                response.raise_for_status()
                result = response.json()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "response": result,
                    "message_ts": result.get("ts"),
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to send Slack message: {e}")
            
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
                "webhook_url": {
                    "type": "string",
                    "description": "Slack webhook URL",
                },
                "token": {
                    "type": "string",
                    "description": "Slack API token",
                },
                "channel": {
                    "type": "string",
                    "description": "Channel ID or name",
                },
                "message": {
                    "type": "string",
                    "description": "Message text",
                },
                "blocks": {
                    "type": "array",
                    "description": "Slack blocks for rich formatting",
                },
                "thread_ts": {
                    "type": "string",
                    "description": "Thread timestamp for threading",
                },
            },
            "required": ["message"],
            "oneOf": [
                {"required": ["webhook_url"]},
                {"required": ["token", "channel"]},
            ],
        }