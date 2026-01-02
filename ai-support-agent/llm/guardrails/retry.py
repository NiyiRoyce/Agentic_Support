# retry guardrail
"""Retry strategies and backoff logic for LLM calls."""

import asyncio
import time
from typing import Callable, Optional, Any, TypeVar, List
from dataclasses import dataclass
from enum import Enum
import random

T = TypeVar('T')


class RetryStrategy(str, Enum):
    """Available retry strategies."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"
    FIBONACCI = "fibonacci"


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, attempts: int, last_error: Exception):
        self.message = message
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(self.message)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: bool = True
    jitter_range: tuple = (0.8, 1.2)
    
    # Retry only on specific errors
    retry_on_errors: Optional[List[type]] = None
    # Don't retry on specific errors
    no_retry_on_errors: Optional[List[type]] = None


class RetryHandler:
    """
    Handles retry logic with various backoff strategies.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._attempt_history = []

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with retry logic.
        """
        last_error = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                # Record attempt
                self._attempt_history.append({
                    'attempt': attempt,
                    'timestamp': time.time(),
                })

                # Execute function
                result = await func(*args, **kwargs)
                
                # Success - return result
                return result

            except Exception as e:
                last_error = e
                
                # Check if we should retry this error
                if not self._should_retry(e):
                    raise e

                # If this was the last attempt, raise
                if attempt >= self.config.max_attempts:
                    raise RetryError(
                        f"Max retry attempts ({self.config.max_attempts}) exceeded",
                        attempts=attempt,
                        last_error=e,
                    )

                # Calculate and apply backoff delay
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

        # This should never be reached due to the raise above
        raise RetryError(
            "Retry logic error",
            attempts=self.config.max_attempts,
            last_error=last_error,
        )

    def _should_retry(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        error_type = type(error)

        # Check no-retry list first (takes precedence)
        if self.config.no_retry_on_errors:
            if any(isinstance(error, err_type) for err_type in self.config.no_retry_on_errors):
                return False

        # Check retry list
        if self.config.retry_on_errors:
            return any(isinstance(error, err_type) for err_type in self.config.retry_on_errors)

        # Default: retry on most errors
        return True

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on retry strategy."""
        if self.config.strategy == RetryStrategy.CONSTANT:
            delay = self.config.initial_delay

        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * attempt

        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.multiplier ** (attempt - 1))

        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self._fibonacci_delay(attempt)

        else:
            delay = self.config.initial_delay

        # Apply max delay cap
        delay = min(delay, self.config.max_delay)

        # Apply jitter if enabled
        if self.config.jitter:
            jitter_min, jitter_max = self.config.jitter_range
            delay *= random.uniform(jitter_min, jitter_max)

        return delay

    def _fibonacci_delay(self, n: int) -> float:
        """Calculate Fibonacci sequence delay."""
        if n <= 2:
            return self.config.initial_delay
        
        fib_prev, fib_curr = 1, 1
        for _ in range(n - 2):
            fib_prev, fib_curr = fib_curr, fib_prev + fib_curr
        
        return self.config.initial_delay * fib_curr

    def get_attempt_history(self) -> List[dict]:
        """Get history of retry attempts."""
        return self._attempt_history.copy()

    def reset_history(self):
        """Reset attempt history."""
        self._attempt_history = []


class AdaptiveRetry:
    """
    Adaptive retry that adjusts strategy based on error patterns.
    """

    def __init__(self, base_config: Optional[RetryConfig] = None):
        self.base_config = base_config or RetryConfig()
        self._error_counts = {}
        self._success_counts = {}
        self._total_attempts = 0

    async def execute(
        self,
        func: Callable,
        error_category: str = "default",
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute with adaptive retry based on historical performance.
        """
        # Get adapted config for this error category
        config = self._get_adapted_config(error_category)
        
        handler = RetryHandler(config)
        
        try:
            result = await handler.execute(func, *args, **kwargs)
            self._record_success(error_category)
            return result
        except Exception as e:
            self._record_failure(error_category, type(e).__name__)
            raise

    def _get_adapted_config(self, category: str) -> RetryConfig:
        """Get config adapted to error category performance."""
        config = RetryConfig(
            max_attempts=self.base_config.max_attempts,
            strategy=self.base_config.strategy,
            initial_delay=self.base_config.initial_delay,
            max_delay=self.base_config.max_delay,
            multiplier=self.base_config.multiplier,
            jitter=self.base_config.jitter,
        )

        # Adapt based on historical data
        if category in self._error_counts:
            error_rate = self._error_counts[category] / max(1, self._total_attempts)
            
            # If error rate is high, increase delays
            if error_rate > 0.5:
                config.initial_delay *= 1.5
                config.max_delay *= 1.5
            
            # If error rate is very high, reduce attempts (fail faster)
            if error_rate > 0.8:
                config.max_attempts = max(2, config.max_attempts - 1)

        return config

    def _record_success(self, category: str):
        """Record successful execution."""
        self._success_counts[category] = self._success_counts.get(category, 0) + 1
        self._total_attempts += 1

    def _record_failure(self, category: str, error_type: str):
        """Record failed execution."""
        self._error_counts[category] = self._error_counts.get(category, 0) + 1
        self._total_attempts += 1

    def get_stats(self) -> dict:
        """Get retry statistics."""
        return {
            'total_attempts': self._total_attempts,
            'error_counts': self._error_counts.copy(),
            'success_counts': self._success_counts.copy(),
        }


class RateLimitRetry:
    """
    Specialized retry handler for rate limit errors.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self._rate_limit_window = {}

    async def execute(
        self,
        func: Callable,
        provider: str = "default",
        *args,
        **kwargs,
    ) -> Any:
        """Execute with rate limit aware retry."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                # Check if we're in a rate limit window
                if self._is_rate_limited(provider):
                    wait_time = self._get_rate_limit_wait(provider)
                    await asyncio.sleep(wait_time)

                result = await func(*args, **kwargs)
                self._clear_rate_limit(provider)
                return result

            except Exception as e:
                error_msg = str(e).lower()
                
                # Detect rate limit errors
                if "rate limit" in error_msg or "429" in error_msg:
                    delay = self._parse_retry_after(error_msg) or (self.base_delay * (2 ** attempt))
                    self._set_rate_limit(provider, delay)
                    
                    if attempt < self.max_attempts:
                        await asyncio.sleep(delay)
                        continue
                
                # Non-rate-limit error
                raise e

        raise RetryError(
            f"Rate limit retry exhausted after {self.max_attempts} attempts",
            attempts=self.max_attempts,
            last_error=Exception("Rate limited"),
        )

    def _parse_retry_after(self, error_msg: str) -> Optional[float]:
        """Parse retry-after header from error message."""
        import re
        match = re.search(r'retry after (\d+)', error_msg)
        if match:
            return float(match.group(1))
        return None

    def _is_rate_limited(self, provider: str) -> bool:
        """Check if provider is currently rate limited."""
        if provider not in self._rate_limit_window:
            return False
        return time.time() < self._rate_limit_window[provider]

    def _get_rate_limit_wait(self, provider: str) -> float:
        """Get remaining wait time for rate limit."""
        if provider not in self._rate_limit_window:
            return 0
        return max(0, self._rate_limit_window[provider] - time.time())

    def _set_rate_limit(self, provider: str, duration: float):
        """Set rate limit window for provider."""
        self._rate_limit_window[provider] = time.time() + duration

    def _clear_rate_limit(self, provider: str):
        """Clear rate limit for provider."""
        if provider in self._rate_limit_window:
            del self._rate_limit_window[provider]