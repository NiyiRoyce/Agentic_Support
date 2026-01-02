# fallback strategies for LLM
"""Fallback strategies for LLM failures."""

import asyncio
from typing import List, Optional, Callable
from dataclasses import dataclass

from llm.providers.base import LLMMessage, LLMResponse, LLMConfig


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class FallbackHandler:
    """
    Handles LLM fallback strategies including:
    - Exponential backoff retry
    - Graceful degradation
    - Canned responses
    """

    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()

    async def retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> LLMResponse:
        """
        Retry function with exponential backoff.
        """
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                result = await func(*args, **kwargs)

                if result.success:
                    return result

                last_error = result.error

            except Exception as e:
                last_error = str(e)

            # Calculate backoff delay
            if attempt < self.config.max_retries - 1:
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

        # All retries exhausted
        return LLMResponse(
            content="",
            model="unknown",
            provider="unknown",
            tokens_used=0,
            cost_usd=0.0,
            metadata={"retries_exhausted": True, "attempts": self.config.max_retries},
            success=False,
            error=f"Max retries exceeded. Last error: {last_error}",
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate backoff delay with optional jitter."""
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay,
        )

        if self.config.jitter:
            import random
            delay *= random.uniform(0.5, 1.5)

        return delay

    def get_canned_response(self, intent: str) -> str:
        """
        Return canned response for common intents when LLM fails.
        """
        canned_responses = {
            "greeting": "Hello! I'm here to help. How can I assist you today?",
            "order_status": "I'm having trouble accessing order information right now. Please try again in a moment or contact support@example.com",
            "product_info": "I'm experiencing technical difficulties. Please visit our website or contact support for product information.",
            "ticket_creation": "I'm unable to create a ticket right now. Please email support@example.com and we'll help you shortly.",
            "escalation": "I apologize for the inconvenience. Please contact our support team directly at support@example.com or call 1-800-SUPPORT.",
            "unknown": "I'm experiencing technical difficulties. Please try again in a moment.",
        }

        return canned_responses.get(intent, canned_responses["unknown"])

    def create_degraded_response(
        self,
        intent: str,
        context: Optional[dict] = None,
    ) -> LLMResponse:
        """
        Create a graceful degraded response when LLM is unavailable.
        """
        canned_content = self.get_canned_response(intent)

        return LLMResponse(
            content=canned_content,
            model="fallback",
            provider="canned",
            tokens_used=0,
            cost_usd=0.0,
            metadata={
                "degraded": True,
                "intent": intent,
                "context": context or {},
            },
            success=True,
        )


class CircuitBreaker:
    """
    Circuit breaker pattern for LLM providers.
    Prevents cascading failures by temporarily disabling failing providers.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = "closed"  # closed, open, half_open
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

    def is_open(self) -> bool:
        """Check if circuit is open (provider disabled)."""
        if self._state == "open":
            # Check if recovery timeout has elapsed
            if self._should_attempt_reset():
                self._state = "half_open"
                self._half_open_calls = 0
                return False
            return True
        return False

    def record_success(self):
        """Record successful call."""
        if self._state == "half_open":
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._reset()
        elif self._state == "closed":
            self._failure_count = 0

    def record_failure(self):
        """Record failed call."""
        import time

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"

        if self._state == "half_open":
            self._state = "open"

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        import time

        if self._last_failure_time is None:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def _reset(self):
        """Reset circuit breaker to closed state."""
        self._state = "closed"
        self._failure_count = 0
        self._half_open_calls = 0

    def get_state(self) -> dict:
        """Get current circuit breaker state for monitoring."""
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time,
        }