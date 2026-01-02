# schemas for tickets agent

from pydantic import BaseModel, Field
from enum import Enum


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    PRODUCT = "product"
    ACCOUNT = "account"
    OTHER = "other"


class TicketAgentInput(BaseModel):
    issue_description: str
    user_info: dict = Field(default_factory=dict)


class TicketAgentOutput(BaseModel):
    ticket_summary: str
    ticket_description: str
    priority: TicketPriority
    category: TicketCategory
    user_response: str