# email notifier
"""Email notification tool"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from execution.tools.base import BaseTool
from execution.models import ToolResult, ToolStatus, ToolCategory
from execution.core.context import ExecutionContext

logger = logging.getLogger(__name__)


class EmailNotificationTool(BaseTool):
    """Send email notifications"""
    
    def __init__(self):
        super().__init__(
            name="send_email",
            description="Send an email notification",
            category=ToolCategory.NOTIFICATION,
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
            # Extract parameters
            smtp_host = params["smtp_host"]
            smtp_port = params.get("smtp_port", 587)
            smtp_username = params["smtp_username"]
            smtp_password = params["smtp_password"]
            
            from_email = params["from_email"]
            to_emails = params["to_emails"]
            subject = params["subject"]
            body = params["body"]
            body_html = params.get("body_html")
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = ", ".join(to_emails) if isinstance(to_emails, list) else to_emails
            
            # Add CC if provided
            if "cc_emails" in params:
                msg["Cc"] = ", ".join(params["cc_emails"])
                to_emails.extend(params["cc_emails"])
            
            # Add text part
            msg.attach(MIMEText(body, "plain"))
            
            # Add HTML part if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html"))
            
            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "sent_to": to_emails,
                    "subject": subject,
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to send email: {e}")
            
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
                "smtp_host": {"type": "string"},
                "smtp_port": {"type": "integer", "default": 587},
                "smtp_username": {"type": "string"},
                "smtp_password": {"type": "string"},
                "from_email": {
                    "type": "string",
                    "format": "email",
                },
                "to_emails": {
                    "oneOf": [
                        {"type": "string", "format": "email"},
                        {
                            "type": "array",
                            "items": {"type": "string", "format": "email"},
                        },
                    ],
                },
                "cc_emails": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                },
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "body_html": {"type": "string"},
            },
            "required": [
                "smtp_host",
                "smtp_username",
                "smtp_password",
                "from_email",
                "to_emails",
                "subject",
                "body",
            ],
        }