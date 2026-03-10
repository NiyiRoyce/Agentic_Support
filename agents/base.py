"""Base agent class for all AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

from llm import LLMRouter, LLMMessage, LLMConfig, LLMResponse
from llm.guardrails import JSONValidator


class AgentType(str, Enum):
    """Types of agents in the system."""
    INTENT = "intent"
    KNOWLEDGE = "knowledge"
    ORDERS = "orders"
    TICKETS = "tickets"
    ESCALATION = "escalation"


@dataclass
class AgentContext:
    """Context passed to agents for decision making."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = None
    user_metadata: Dict[str, Any] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_metadata is None:
            self.user_metadata = {}


@dataclass
class AgentResult:
    """Standardized result from agent execution."""
    success: bool
    data: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    agent_type: AgentType
    reasoning: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """
    Base class for all AI agents.
    
    Agents are pure functions that:
    1. Take structured input (message + context)
    2. Make decisions using LLMs
    3. Return structured output (AgentResult)
    4. Have NO side effects (no API calls, no database writes)
    """
    
    def __init__(
        self,
        llm_router: LLMRouter,
        agent_type: AgentType,
        default_config: Optional[LLMConfig] = None,
    ):
        self.llm_router = llm_router
        self.agent_type = agent_type
        self.default_config = default_config or LLMConfig(
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1000,
        )
        self.json_validator = JSONValidator()
    
    @abstractmethod
    async def execute(
        self,
        user_message: str,
        context: AgentContext,
        **kwargs,
    ) -> AgentResult:
        """
        Execute agent logic.
        
        Args:
            user_message: The user's input message
            context: Contextual information (history, metadata, etc)
            **kwargs: Additional agent-specific parameters
            
        Returns:
            AgentResult with decision/data
        """
        pass
    
    @abstractmethod
    def build_prompt(
        self,
        user_message: str,
        context: AgentContext,
        **kwargs,
    ) -> str:
        """
        Build the prompt for the LLM.
        
        Args:
            user_message: The user's input
            context: Contextual information
            **kwargs: Additional parameters
            
        Returns:
            Formatted prompt string
        """
        pass
    
    async def _call_llm(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """
        Internal method to call LLM with error handling.
        
        Args:
            messages: List of messages for the LLM
            config: LLM configuration (uses default if not provided)
            
        Returns:
            LLM response
        """
        llm_config = config or self.default_config
        
        try:
            response = await self.llm_router.complete(
                messages=messages,
                llm_config=llm_config,
            )
            return response
        except Exception as e:
            # Return failed response
            return LLMResponse(
                content="",
                model="unknown",
                provider="unknown",
                tokens_used=0,
                cost_usd=0.0,
                metadata={"error": str(e)},
                success=False,
                error=str(e),
            )
    
    def _create_success_result(
        self,
        data: Dict[str, Any],
        confidence: float,
        reasoning: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Helper to create success result."""
        return AgentResult(
            success=True,
            data=data,
            confidence=confidence,
            agent_type=self.agent_type,
            reasoning=reasoning,
            metadata=metadata or {},
        )
    
    def _create_error_result(
        self,
        error: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Helper to create error result."""
        return AgentResult(
            success=False,
            data=data or {},
            confidence=0.0,
            agent_type=self.agent_type,
            error=error,
            metadata=metadata or {},
        )
    
    def _parse_llm_json(
        self,
        response: LLMResponse,
        schema: Optional[type] = None,
    ) -> tuple[bool, Optional[Dict], Optional[str]]:
        """
        Parse and validate JSON from LLM response.
        
        Args:
            response: LLM response
            schema: Optional Pydantic schema for validation
            
        Returns:
            (is_valid, parsed_data, error_message)
        """
        if not response.success:
            return False, None, f"LLM call failed: {response.error}"
        
        # Validate JSON
        if schema:
            is_valid, parsed, error = self.json_validator.validate_with_schema(
                response.content,
                schema,
            )
            if is_valid:
                return True, parsed.dict(), None
            return False, None, error
        else:
            is_valid, parsed, error = self.json_validator.validate_json(
                response.content
            )
            return is_valid, parsed, error
    
    def _format_conversation_history(
        self,
        context: AgentContext,
        max_messages: int = 5,
    ) -> str:
        """
        Format conversation history for inclusion in prompts.
        
        Args:
            context: Agent context with conversation history
            max_messages: Maximum number of messages to include
            
        Returns:
            Formatted conversation history string
        """
        if not context.conversation_history:
            return "No previous conversation"
        
        # Take last N messages
        recent = context.conversation_history[-max_messages:]
        
        formatted = []
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content}")
        
        return "\n".join(formatted)
    
    async def validate_output(
        self,
        result: AgentResult,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate agent output before returning.
        
        Args:
            result: The agent result to validate
            
        Returns:
            (is_valid, error_message)
        """
        # Basic validation
        if not isinstance(result, AgentResult):
            return False, "Result must be AgentResult instance"
        
        if result.confidence < 0.0 or result.confidence > 1.0:
            return False, "Confidence must be between 0.0 and 1.0"
        
        if result.success and not result.data:
            return False, "Success result must contain data"
        
        return True, None
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent metrics for monitoring.
        Override in subclasses for specific metrics.
        """
        return {
            "agent_type": self.agent_type.value,
            "default_model": self.default_config.model,
            "default_temperature": self.default_config.temperature,
        }