# intent agent implementation (stub)
"""Intent classification agent."""

from typing import Optional

from agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from agents.intent.schemas import IntentClassification, IntentType
from agents.intent.prompts import IntentPrompts
from llm import LLMRouter, LLMMessage, LLMConfig


class IntentAgent(BaseAgent):
    """
    Agent responsible for classifying user intent.
    
    This agent analyzes user messages and determines what they're trying to do,
    enabling routing to the appropriate specialized agent.
    """
    
    def __init__(
        self,
        llm_router: LLMRouter,
        default_config: Optional[LLMConfig] = None,
    ):
        super().__init__(
            llm_router=llm_router,
            agent_type=AgentType.INTENT,
            default_config=default_config or LLMConfig(
                model="gpt-4o-mini",
                temperature=0.3,  # Lower temperature for more consistent classification
                max_tokens=500,
                json_mode=True,
            ),
        )
        self.prompts = IntentPrompts()
    
    async def execute(
        self,
        user_message: str,
        context: AgentContext,
        **kwargs,
    ) -> AgentResult:
        """
        Classify user intent from their message.
        
        Args:
            user_message: The user's input message
            context: Contextual information including history
            
        Returns:
            AgentResult with intent classification
        """
        # Build prompt
        prompt = self.build_prompt(user_message, context)
        
        # Prepare messages
        messages = [
            LLMMessage(role="system", content=self.prompts.SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        
        # Call LLM
        response = await self._call_llm(messages, self.default_config)
        
        # Parse response
        is_valid, parsed, error = self._parse_llm_json(
            response,
            schema=IntentClassification,
        )
        
        if not is_valid:
            return self._create_error_result(
                error=f"Failed to parse intent: {error}",
                metadata={
                    "raw_response": response.content,
                    "tokens_used": response.tokens_used,
                    "cost": response.cost_usd,
                }
            )
        
        # Extract classification
        classification = parsed
        
        # Determine suggested agent based on intent
        suggested_agent = self._map_intent_to_agent(classification["intent"])
        
        # Build result
        return self._create_success_result(
            data={
                "intent": classification["intent"],
                "requires_clarification": classification["requires_clarification"],
                "clarification_question": classification.get("clarification_question"),
                "extracted_entities": classification.get("extracted_entities", {}),
                "suggested_agent": suggested_agent,
            },
            confidence=classification["confidence"],
            reasoning=classification["reasoning"],
            metadata={
                "tokens_used": response.tokens_used,
                "cost": response.cost_usd,
                "model": response.model,
                "provider": response.provider,
            }
        )
    
    def build_prompt(
        self,
        user_message: str,
        context: AgentContext,
        **kwargs,
    ) -> str:
        """Build prompt for intent classification."""
        # Format conversation history
        history = self._format_conversation_history(context, max_messages=3)
        
        # Build user prompt
        return self.prompts.build_user_prompt(
            user_message=user_message,
            conversation_history=history,
            user_metadata=context.user_metadata,
        )
    
    def _map_intent_to_agent(self, intent: str) -> Optional[str]:
        """Map intent to the appropriate agent type."""
        intent_to_agent = {
            IntentType.ORDER_STATUS: "orders",
            IntentType.PRODUCT_INFO: "knowledge",
            IntentType.TICKET_CREATION: "tickets",
            IntentType.ACCOUNT_MANAGEMENT: "knowledge",
            IntentType.RETURNS_REFUNDS: "tickets",
            IntentType.GENERAL_INQUIRY: "knowledge",
            IntentType.GREETING: "knowledge",
            IntentType.ESCALATION: "escalation",
            IntentType.UNKNOWN: None,
        }
        return intent_to_agent.get(intent)
    
    async def generate_clarification(
        self,
        user_message: str,
        possible_intents: list,
    ) -> str:
        """
        Generate a clarification question when intent is ambiguous.
        
        Args:
            user_message: The ambiguous user message
            possible_intents: List of possible intents
            
        Returns:
            Clarification question string
        """
        prompt = self.prompts.build_clarification_prompt(
            user_message=user_message,
            possible_intents=possible_intents,
        )
        
        messages = [
            LLMMessage(role="system", content=self.prompts.SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        
        # Use lower max_tokens for clarification
        config = LLMConfig(
            model=self.default_config.model,
            temperature=0.7,
            max_tokens=150,
            json_mode=False,  # Plain text response
        )
        
        response = await self._call_llm(messages, config)
        
        if response.success:
            return response.content.strip()
        else:
            # Fallback clarification
            return "I want to make sure I help you with the right thing. Could you provide a bit more detail about what you need?"