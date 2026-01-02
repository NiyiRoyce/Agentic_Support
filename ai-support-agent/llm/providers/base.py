"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class LLMMessage:
    """Structured message for LLM conversations."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    provider: str
    tokens_used: int
    cost_usd: float
    metadata: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


@dataclass
class LLMConfig:
    """Configuration for LLM calls."""
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    json_mode: bool = False
    timeout: int = 30


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, default_model: str):
        self.api_key = api_key
        self.default_model = default_model

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate completion from messages."""
        pass

    @abstractmethod
    def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost in USD for token usage."""
        pass

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text for given model."""
        pass

    def _create_default_config(self, overrides: Optional[LLMConfig] = None) -> LLMConfig:
        """Create config with defaults and overrides."""
        if overrides:
            return overrides
        return LLMConfig(model=self.default_model)