# schemas for orders agent
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderAgentInput(BaseModel):
    order_id: Optional[str] = None
    user_email: Optional[str] = None
    query_type: str = Field(description="Type of order query")


class OrderAgentOutput(BaseModel):
    order_info: dict
    response_message: str
    confidence: float
    needs_escalation: bool = False
