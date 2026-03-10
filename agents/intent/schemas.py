# schemas for intent agent
"""Schemas for Intent Agent."""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class IntentType(str, Enum):
    """Available intent types."""
    ORDER_STATUS = "order_status"
    PRODUCT_INFO = "product_info"
    TICKET_CREATION = "ticket_creation"
    ACCOUNT_MANAGEMENT = "account_management"
    RETURNS_REFUNDS = "returns_refunds"
    GENERAL_INQUIRY = "general_inquiry"
    GREETING = "greeting"
    ESCALATION = "escalation"
    UNKNOWN = "unknown"


class IntentClassification(BaseModel):
    """Intent classification result from LLM."""
    intent: IntentType = Field(description="Classified intent")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for classification"
    )
    reasoning: str = Field(description="Explanation of classification")
    requires_clarification: bool = Field(
        default=False,
        description="Whether user input is ambiguous"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask user if clarification needed"
    )
    extracted_entities: dict = Field(
        default_factory=dict,
        description="Extracted entities from user message"
    )


class IntentAgentInput(BaseModel):
    """Input for Intent Agent."""
    user_message: str
    conversation_history: List[dict] = Field(default_factory=list)
    user_metadata: dict = Field(default_factory=dict)


class IntentAgentOutput(BaseModel):
    """Output from Intent Agent."""
    intent: IntentType
    confidence: float
    reasoning: str
    requires_clarification: bool
    clarification_question: Optional[str] = None
    extracted_entities: dict = Field(default_factory=dict)
    suggested_agent: Optional[str] = None