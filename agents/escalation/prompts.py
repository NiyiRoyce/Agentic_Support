# prompts for escalation agent

class EscalationPrompts:
    SYSTEM_PROMPT = """You are an escalation decision system.
    
    Determine if customer conversations need human agent intervention."""
    
    @staticmethod
    def build_escalation_prompt(conversation_history: str) -> str:
        return f"""Evaluate if this conversation needs escalation to a human agent:

{conversation_history}

Escalate if:
- Customer is frustrated/angry
- Issue is complex beyond AI
- Customer requests human
- Sensitive topic (refunds, complaints)
- AI failed multiple times

Respond with JSON:
{{
  "should_escalate": true/false,
  "reason": "customer_request/frustration/complex_issue/policy_exception/sensitive_topic/ai_failure",
  "urgency": "low/medium/high",
  "department": "billing/technical/general",
  "handoff_notes": "brief context for human agent"
}}"""

