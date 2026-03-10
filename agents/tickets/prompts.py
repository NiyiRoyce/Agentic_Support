# prompts for tickets agent

class TicketPrompts:
    SYSTEM_PROMPT = """You are a support ticket creation assistant.
    
    Analyze customer issues and create well-structured support tickets."""
    
    @staticmethod
    def build_ticket_creation_prompt(issue: str, user_info: dict) -> str:
        return f"""Create a support ticket for this customer issue:

Issue: "{issue}"
User Info: {user_info}

Generate JSON with:
{{
  "ticket_summary": "brief title",
  "ticket_description": "detailed description for support team",
  "priority": "low/medium/high/urgent",
  "category": "technical/billing/product/account/other",
  "user_response": "empathetic message confirming ticket creation"
}}"""
