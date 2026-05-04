"""Unit tests for IntentAgent."""

import pytest
from unittest.mock import AsyncMock

from agents.intent.agent import IntentAgent
from agents.base import AgentContext, AgentResult
from agents.intent.schemas import IntentType
from llm import LLMRouter, LLMConfig, LLMMessage
from llm.providers.mock import MockLLMProvider
from llm.providers.base import LLMProvider


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MockLLMProvider()
    # Add a successful response
    provider.add_response(
        content='{"intent": "order_status", "confidence": 0.9, "reasoning": "User asked about order", "requires_clarification": false}',
        tokens=50,
        cost=0.005
    )
    return provider


@pytest.fixture
def llm_router(mock_llm_provider):
    """Create LLM router with mock provider."""
    return LLMRouter(
        providers={LLMProvider.OPENAI: mock_llm_provider}
    )


@pytest.fixture
def intent_agent(llm_router):
    """Create IntentAgent instance."""
    return IntentAgent(llm_router=llm_router)


@pytest.fixture
def agent_context():
    """Create test agent context."""
    return AgentContext(
        session_id="test-session",
        user_id="test-user",
        conversation_history=[],
        user_metadata={}
    )


@pytest.mark.asyncio
async def test_intent_agent_execute_success(intent_agent, agent_context):
    """Test successful intent classification."""
    user_message = "Where is my order #12345?"

    result = await intent_agent.execute(user_message, agent_context)

    assert result.success is True
    assert result.data["intent"] == IntentType.ORDER_STATUS
    assert result.data["suggested_agent"] == "orders"
    assert result.confidence == 0.9
    assert "tokens_used" in result.metadata


@pytest.mark.asyncio
async def test_intent_agent_execute_invalid_json(intent_agent, agent_context, mock_llm_provider):
    """Test handling of invalid JSON response."""
    # Override with invalid JSON
    mock_llm_provider.responses = [("invalid json", 10, 0.001)]

    user_message = "Hello"

    result = await intent_agent.execute(user_message, agent_context)

    assert result.success is False
    assert "Failed to parse intent" in result.error


def test_map_intent_to_agent(intent_agent):
    """Test intent to agent mapping."""
    assert intent_agent._map_intent_to_agent(IntentType.ORDER_STATUS) == "orders"
    assert intent_agent._map_intent_to_agent(IntentType.PRODUCT_INFO) == "knowledge"
    assert intent_agent._map_intent_to_agent(IntentType.TICKET_CREATION) == "tickets"
    assert intent_agent._map_intent_to_agent("unknown_intent") is None


def test_build_prompt(intent_agent, agent_context):
    """Test prompt building."""
    user_message = "Test message"
    prompt = intent_agent.build_prompt(user_message, agent_context)

    assert user_message in prompt
    assert "Classify the customer's intent" in prompt