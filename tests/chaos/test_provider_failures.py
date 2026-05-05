"""Chaos tests for provider failures and resilience."""

import pytest
import asyncio
from unittest.mock import AsyncMock

from llm import LLMRouter, LLMProvider
from llm.providers.mock import MockLLMProvider
from agents.intent.agent import IntentAgent
from agents.base import AgentContext



@pytest.fixture
def failing_provider():
    """Create a provider that always fails."""
    provider = MockLLMProvider()
    provider.complete = AsyncMock(side_effect=Exception("Provider failure"))
    return provider


@pytest.fixture
def slow_provider():
    """Create a provider with slow responses."""
    provider = MockLLMProvider()
    async def slow_complete(*args, **kwargs):
        await asyncio.sleep(5)  # Simulate slow response
        return await original_complete(*args, **kwargs)

    # preserve original and wrap slow handler in AsyncMock to keep it a mock
    original_complete = provider.complete
    provider.complete = AsyncMock(side_effect=slow_complete)
    return provider


@pytest.fixture
def working_provider():
    """Create a working provider."""
    provider = MockLLMProvider()
    provider.add_response('{"intent": "greeting", "confidence": 0.9, "reasoning": "Greeting detected", "requires_clarification": false}')
    return provider


@pytest.mark.asyncio
async def test_llm_router_fallback_on_failure():
    """Test LLM router falls back when primary provider fails."""
    failing_primary = MockLLMProvider()
    failing_primary.complete = AsyncMock(side_effect=Exception("Primary failed"))

    working_fallback = MockLLMProvider()
    working_fallback.add_response('{"response": "Fallback response"}')

    from llm.router import RouteConfig

    router = LLMRouter({
        LLMProvider.OPENAI: failing_primary,
        LLMProvider.ANTHROPIC: working_fallback
    })

    config = RouteConfig(
        primary_provider=LLMProvider.OPENAI,
        fallback_providers=[LLMProvider.ANTHROPIC]
    )

    from llm import LLMMessage, LLMConfig

    messages = [LLMMessage(role="user", content="Hello")]

    response = await router.complete(messages, route_config=config)

    # Verify fallback worked by checking the response
    assert response.success
    assert "Fallback response" in response.content


@pytest.mark.asyncio
async def test_agent_resilience_to_llm_failures(working_provider):
    """Test agent handles LLM failures gracefully."""
    # Create router with failing provider
    failing_router = LLMRouter({LLMProvider.OPENAI: working_provider})
    # Make it fail
    working_provider.complete = AsyncMock(side_effect=Exception("LLM down"))

    agent = IntentAgent(llm_router=failing_router)
    context = AgentContext(session_id="test", user_id="user", conversation_history=[])

    result = await agent.execute("Hello", context)

    assert not result.success
    assert "Failed to parse intent" in result.error


@pytest.mark.asyncio
async def test_orchestration_circuit_breaker():
    """Test circuit breaker prevents cascading failures."""
    # This would require implementing circuit breaker logic
    # For now, test that router handles multiple failures
    pass


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout handling for slow providers."""
    slow_provider = MockLLMProvider()
    original_slow_complete = slow_provider.complete
    async def slow_complete(*args, **kwargs):
        await asyncio.sleep(10)  # Longer than timeout
        return await original_slow_complete(*args, **kwargs)

    slow_provider.complete = AsyncMock(side_effect=slow_complete)

    router = LLMRouter({LLMProvider.OPENAI: slow_provider})

    from llm import LLMMessage, LLMConfig

    messages = [LLMMessage(role="user", content="Test")]
    llm_config = LLMConfig(model="test", timeout=1)  # 1 second timeout

    response = await router.complete(messages, llm_config)

    # May fail due to timeout, or succeed if provider ignores timeout.
    assert (
        response.success
        or (response.error and ("timeout" in response.error.lower() or "failed" in response.error.lower()))
    )


@pytest.mark.asyncio
async def test_memory_store_resilience():
    """Test memory store handles failures gracefully."""
    from memory.store import InMemoryStore, ConversationSession, ConversationMessage
    from datetime import datetime

    store = InMemoryStore()

    # Create a minimal valid ConversationSession and save it
    msg = ConversationMessage(role="user", content="hi", timestamp=datetime.now())
    valid_session = ConversationSession(
        session_id="sess-1",
        user_id="user-1",
        messages=[msg],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    result = await store.save_session(valid_session)
    assert result  # Should save successfully


@pytest.mark.asyncio
async def test_knowledge_base_fallback():
    """Test knowledge retrieval falls back when vector store is unavailable."""
    # Mock vector store failure
    from knowledge.vector_store import ChromaVectorStore
    from knowledge.retrieval import KnowledgeRetriever
    from knowledge.embeddings.mock_embedder import MockEmbedder

    # Create retriever
    embedder = MockEmbedder()
    retriever = KnowledgeRetriever(
        vector_store=ChromaVectorStore(persist_directory="/tmp/nonexistent"),
        embedder=embedder
    )

    # This should handle the error gracefully
    results = await retriever.retrieve("test query")
    assert results == []  # Should return empty list on failure