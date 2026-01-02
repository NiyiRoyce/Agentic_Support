# prompts for intent agent
"""Prompts for Intent Agent."""

from typing import Dict, Any


class IntentPrompts:
    """Prompt templates for intent classification."""
    
    SYSTEM_PROMPT = """You are an intent classification system for a customer support AI agent.

Your job is to analyze customer messages and determine their primary intent with high accuracy.

Available intents:
- order_status: Customer asking about order tracking, delivery, shipment status
- product_info: Customer asking about product details, specifications, availability, pricing
- ticket_creation: Customer reporting an issue, problem, or requesting technical support
- account_management: Customer asking about account, login, password, profile settings
- returns_refunds: Customer asking about returns, refunds, exchanges, cancellations
- general_inquiry: General questions about company, policies, hours, contact info
- greeting: Customer greeting or starting conversation (hello, hi, hey)
- escalation: Customer explicitly requesting human agent or expressing frustration
- unknown: Intent is unclear or doesn't fit other categories

Guidelines:
1. Consider conversation history for context
2. Look for key phrases and entities (order numbers, product names, etc.)
3. Be confident in your classification (aim for >0.7 confidence)
4. Set requires_clarification=true if message is ambiguous
5. Extract relevant entities (order_id, product_name, etc.)

You must respond ONLY with valid JSON, no other text."""
    
    @staticmethod
    def build_user_prompt(
        user_message: str,
        conversation_history: str,
        user_metadata: Dict[str, Any],
    ) -> str:
        """Build user prompt for intent classification."""
        return f"""Classify the customer's intent based on their message.

USER MESSAGE: "{user_message}"

CONVERSATION HISTORY:
{conversation_history}

USER METADATA:
{user_metadata}

Respond with JSON in this exact format:
{{
  "intent": "intent_name",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "requires_clarification": true/false,
  "clarification_question": "question to ask if clarification needed (or null)",
  "extracted_entities": {{
    "order_id": "extracted order number if present",
    "product_name": "extracted product name if present",
    "email": "extracted email if present"
  }}
}}"""

    @staticmethod
    def build_clarification_prompt(
        user_message: str,
        possible_intents: list,
    ) -> str:
        """Build prompt for generating clarification question."""
        return f"""The user's message is ambiguous: "{user_message}"

Possible intents: {', '.join(possible_intents)}

Generate a friendly, natural clarification question that helps determine the user's true intent.

The question should:
1. Acknowledge their message
2. Present the options clearly
3. Be conversational and helpful

Example: "I'd be happy to help! Are you asking about an existing order, or would you like information about our products?"

Respond with ONLY the clarification question text, no JSON."""