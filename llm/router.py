# LLM router
"""LLM router with fallback and load balancing."""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from llm.providers.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMProvider,
)
from llm.providers.openai import OpenAIProvider
from llm.providers.anthropic import AnthropicProvider


class RoutingStrategy(str, Enum):
    """Routing strategies for LLM selection."""
    COST = "cost"  # Choose cheapest option
    LATENCY = "latency"  # Choose fastest option
    QUALITY = "quality"  # Choose most capable model
    PRIMARY = "primary"  # Always use primary provider


@dataclass
class RouteConfig:
    """Configuration for LLM routing."""
    strategy: RoutingStrategy = RoutingStrategy.PRIMARY
    primary_provider: LLMProvider = LLMProvider.OPENAI
    fallback_providers: List[LLMProvider] = None
    max_retries: int = 2
    timeout: int = 30


class LLMRouter:
    """
    Routes LLM requests to appropriate providers with fallback support.
    """

    def __init__(
        self,
        providers: Dict[LLMProvider, BaseLLMProvider],
        route_config: Optional[RouteConfig] = None,
    ):
        self.providers = providers
        self.config = route_config or RouteConfig()
        self._circuit_breaker = {}  # Track provider health

    async def complete(
        self,
        messages: List[LLMMessage],
        llm_config: Optional[LLMConfig] = None,
        route_config: Optional[RouteConfig] = None,
    ) -> LLMResponse:
        """
        Route completion request to appropriate provider with fallbacks.
        """
        cfg = route_config or self.config

        # Determine provider order based on strategy
        provider_order = self._determine_provider_order(cfg)

        last_error = None

        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            # Check circuit breaker
            if self._is_circuit_open(provider_name):
                continue

            # Attempt completion
            try:
                response = await provider.complete(messages, llm_config)

                if response.success:
                    self._record_success(provider_name)
                    return response
                else:
                    last_error = response.error
                    self._record_failure(provider_name)

            except Exception as e:
                last_error = str(e)
                self._record_failure(provider_name)
                continue

        # All providers failed
        return LLMResponse(
            content="",
            model="unknown",
            provider="none",
            tokens_used=0,
            cost_usd=0.0,
            metadata={"all_providers_failed": True},
            success=False,
            error=f"All providers failed. Last error: {last_error}",
        )

    def _determine_provider_order(self, config: RouteConfig) -> List[LLMProvider]:
        """Determine provider order based on routing strategy."""
        if config.strategy == RoutingStrategy.PRIMARY:
            order = [config.primary_provider]
            if config.fallback_providers:
                order.extend(config.fallback_providers)
            return order

        elif config.strategy == RoutingStrategy.COST:
            # Order by cost (cheapest first)
            return [
                LLMProvider.OPENAI,  # gpt-4o-mini is cheapest
                LLMProvider.ANTHROPIC,
            ]

        elif config.strategy == RoutingStrategy.QUALITY:
            # Order by quality
            return [
                LLMProvider.ANTHROPIC,  # Claude Sonnet 4.5 is best
                LLMProvider.OPENAI,
            ]

        else:  # LATENCY
            return [
                LLMProvider.OPENAI,  # Generally faster
                LLMProvider.ANTHROPIC,
            ]

    def _is_circuit_open(self, provider: LLMProvider) -> bool:
        """Check if circuit breaker is open for provider."""
        breaker = self._circuit_breaker.get(provider, {"failures": 0})
        # Open circuit after 3 consecutive failures
        return breaker.get("failures", 0) >= 3

    def _record_success(self, provider: LLMProvider):
        """Record successful request."""
        self._circuit_breaker[provider] = {"failures": 0}

    def _record_failure(self, provider: LLMProvider):
        """Record failed request."""
        breaker = self._circuit_breaker.get(provider, {"failures": 0})
        breaker["failures"] = breaker.get("failures", 0) + 1
        self._circuit_breaker[provider] = breaker

    async def complete_with_retry(
        self,
        messages: List[LLMMessage],
        llm_config: Optional[LLMConfig] = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """Complete with exponential backoff retry."""
        for attempt in range(max_retries):
            response = await self.complete(messages, llm_config)

            if response.success:
                return response

            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

        return response

    def get_provider_stats(self) -> Dict:
        """Get circuit breaker stats for monitoring."""
        return {
            provider.value: self._circuit_breaker.get(provider, {"failures": 0})
            for provider in LLMProvider
        }