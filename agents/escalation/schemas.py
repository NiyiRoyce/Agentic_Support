# schemas for escalation agent

from pydantic import BaseModel, Field
from enum import Enum


class EscalationReason(str, Enum):
    CUSTOMER_REQUEST = "customer_request"
    FRUSTRATION = "frustration"
    COMPLEX_ISSUE = "complex_issue"
    POLICY_EXCEPTION = "policy_exception"
    SENSITIVE_TOPIC = "sensitive_topic"
    AI_FAILURE = "ai_failure"


class EscalationUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EscalationAgentOutput(BaseModel):
    should_escalate: bool
    reason: EscalationReason
    urgency: EscalationUrgency
    department: str
    handoff_notes: str
