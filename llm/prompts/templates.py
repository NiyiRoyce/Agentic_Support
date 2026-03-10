"""Prompt templates for various agent tasks."""

from typing import Dict, Any


class PromptTemplates:
    """
    Centralized prompt templates for AI support agent.
    """

    @staticmethod
    def intent_classification(user_message: str, context: Dict[str, Any]) -> str:
        """Prompt for intent classification."""
        return f"""You are an intent classification system for a customer support agent.

Analyze the user's message and determine their primary intent.

Available intents:
- order_status: User asking about order status, tracking, delivery
- product_info: User asking about product details, specifications, availability
- ticket_creation: User reporting an issue or requesting support
- account_management: User asking about account, login, password
- returns_refunds: User asking about returns, refunds, cancellations
- general_inquiry: General questions about the company, policies, etc.
- greeting: User greeting or starting conversation
- escalation: Issue requires human agent intervention

User message: "{user_message}"

Context: {context}

Respond ONLY with a JSON object:
{{
  "intent": "intent_name",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "requires_clarification": true/false
}}"""

    @staticmethod
    def knowledge_retrieval(question: str, context: str) -> str:
        """Prompt for RAG-based knowledge retrieval."""
        return f"""You are a helpful customer support assistant. Answer the user's question based on the provided knowledge base context.

Rules:
1. Only use information from the provided context
2. If the context doesn't contain the answer, say "I don't have that information"
3. Be concise but complete
4. Use a friendly, professional tone
5. If relevant, include specific details like order numbers, dates, or policies

User question: "{question}"

Knowledge base context:
{context}

Provide a helpful answer based on the context above."""

    @staticmethod
    def order_status_query(order_id: str, order_data: Dict[str, Any]) -> str:
        """Prompt for order status response."""
        return f"""You are a customer support agent. Provide a friendly, informative response about the order status.

Order ID: {order_id}
Order Data: {order_data}

Create a natural, conversational response that:
1. Confirms the order number
2. Explains the current status
3. Provides estimated delivery if available
4. Offers to help with anything else

Keep it brief but warm and helpful."""

    @staticmethod
    def ticket_creation(issue_description: str, user_info: Dict[str, Any]) -> str:
        """Prompt for ticket creation assistance."""
        return f"""You are creating a support ticket for a customer issue.

Issue description: "{issue_description}"
User info: {user_info}

Generate a JSON response with:
{{
  "ticket_summary": "brief title for the ticket",
  "ticket_description": "detailed description for support team",
  "priority": "low/medium/high",
  "category": "technical/billing/product/other",
  "user_response": "friendly message to send to the user confirming ticket creation"
}}

Make the user_response empathetic and reassuring."""

    @staticmethod
    def escalation_check(conversation_history: str) -> str:
        """Prompt to determine if escalation is needed."""
        return f"""You are evaluating whether a customer support conversation needs escalation to a human agent.

Conversation history:
{conversation_history}

Escalate if:
- Customer is frustrated or angry (multiple negative messages)
- Issue is complex and beyond AI capabilities
- Customer explicitly requests human agent
- Issue involves sensitive topics (refunds, complaints, legal)
- AI has failed to resolve issue after multiple attempts

Respond ONLY with JSON:
{{
  "should_escalate": true/false,
  "reason": "brief explanation",
  "urgency": "low/medium/high",
  "suggested_department": "billing/technical/general"
}}"""

    @staticmethod
    def response_refinement(draft_response: str, user_context: Dict[str, Any]) -> str:
        """Prompt to refine and improve a draft response."""
        return f"""You are refining a customer support response for quality and tone.

Draft response: "{draft_response}"

User context: {user_context}

Improve the response to:
1. Make it more friendly and empathetic
2. Add personalization where appropriate
3. Ensure it's clear and actionable
4. Keep it concise (2-3 sentences unless more detail needed)
5. End with an offer to help further

Provide only the improved response text."""

    @staticmethod
    def clarification_request(ambiguous_query: str, possible_intents: list) -> str:
        """Prompt to generate clarification question."""
        return f"""The user's message is ambiguous: "{ambiguous_query}"

Possible interpretations: {possible_intents}

Generate a friendly, natural clarification question that helps determine the user's true intent.
The question should:
1. Acknowledge their message
2. Present the options clearly
3. Be conversational, not robotic

Example: "I'd be happy to help! Are you asking about [option A] or [option B]?"

Provide only the clarification question text."""

    @staticmethod
    def sentiment_analysis(message: str) -> str:
        """Prompt for sentiment analysis."""
        return f"""Analyze the sentiment of this customer message.

Message: "{message}"

Respond ONLY with JSON:
{{
  "sentiment": "positive/neutral/negative",
  "confidence": 0.0-1.0,
  "emotion": "happy/frustrated/confused/angry/neutral",
  "urgency": "low/medium/high"
}}"""