"""Mock LLM provider for testing."""

from typing import List, Optional
from llm.providers.base import BaseLLMProvider, LLMConfig, LLMMessage, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider that returns predetermined responses."""

    def __init__(self, api_key: str = "mock_key", default_model: str = "mock-model"):
        super().__init__(api_key, default_model)
        self.call_count = 0
        self.responses = []  # List of responses to return in order

    def add_response(self, content: str, tokens: int = 100, cost: float = 0.01) -> None:
        """Add a response to the queue."""
        self.responses.append((content, tokens, cost))

    async def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Return next queued response or default."""
        self.call_count += 1

        if self.responses:
            content, tokens, cost = self.responses.pop(0)
        else:
            # Default response
            content = "Mock response"
            tokens = 10
            cost = 0.001

        model = config.model if config else self.default_model

        return LLMResponse(
            content=content,
            model=model,
            provider="mock",
            tokens_used=tokens,
            cost_usd=cost,
            metadata={"mock_call": self.call_count},
            success=True,
        )

    def estimate_cost(self, tokens: int, model: str) -> float:
        """Mock cost estimation."""
        return tokens * 0.0001

    def count_tokens(self, text: str, model: str) -> int:
        """Mock token counting - rough estimate."""
        return len(text.split()) * 1.3  # Rough approximation
