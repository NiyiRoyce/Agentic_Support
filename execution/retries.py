"""Retry strategies for resilient execution.

Provides configurable retry mechanisms with different backoff strategies:
- Immediate: Retry immediately
- Linear: Linear backoff (1s, 2s, 3s, ...)
- Exponential: Exponential backoff (1s, 2s, 4s, 8s, ...)
- Fibonacci: Fibonacci backoff (1s, 1s, 2s, 3s, 5s, ...)
"""

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Type, TypeVar, Union, List, Tuple
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Available retry strategies."""
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    CUSTOM = "custom"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: bool = True
    jitter_range: Tuple[float, float] = (0.5, 1.5)
    exponential_base: float = 2.0


class BackoffCalculator(ABC):
    """Base class for backoff calculation strategies."""

    @abstractmethod
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for given attempt number."""
        pass


class ImmediateBackoff(BackoffCalculator):
    """No delay - retry immediately."""

    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        return 0.0


class LinearBackoff(BackoffCalculator):
    """Linear backoff: delay = initial_delay * attempt."""

    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        delay = config.initial_delay * (attempt + 1)
        return min(delay, config.max_delay)


class ExponentialBackoff(BackoffCalculator):
    """Exponential backoff: delay = initial_delay * (base ^ attempt)."""

    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        delay = config.initial_delay * (
            config.exponential_base ** attempt
        )
        return min(delay, config.max_delay)


class FibonacciBackoff(BackoffCalculator):
    """Fibonacci backoff: delay increases based on Fibonacci sequence."""

    _fibonacci_cache = [1, 1]

    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        # Generate Fibonacci numbers as needed
        while len(self._fibonacci_cache) <= attempt:
            self._fibonacci_cache.append(
                self._fibonacci_cache[-1] + self._fibonacci_cache[-2]
            )
        
        delay = config.initial_delay * self._fibonacci_cache[attempt]
        return min(delay, config.max_delay)


class RetryExecutor:
    """Executes functions with configurable retry logic."""

    _backoff_strategies = {
        RetryStrategy.IMMEDIATE: ImmediateBackoff(),
        RetryStrategy.LINEAR: LinearBackoff(),
        RetryStrategy.EXPONENTIAL: ExponentialBackoff(),
        RetryStrategy.FIBONACCI: FibonacciBackoff(),
    }

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    async def execute(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        **kwargs,
    ) -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            retryable_exceptions: Exceptions to retry on (default: all exceptions)
            **kwargs: Keyword arguments
            
        Returns:
            Result from function
            
        Raises:
            MaxRetriesExceeded: If all retries exhausted
        """
        retryable_exceptions = retryable_exceptions or [Exception]
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        f"Function succeeded on attempt {attempt + 1}/"
                        f"{self.config.max_attempts}"
                    )
                
                return result
            
            except BaseException as e:
                # Check if exception is retryable
                if not any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                    raise
                
                last_exception = e
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Function failed (attempt {attempt + 1}/"
                        f"{self.config.max_attempts}): {str(e)[:100]}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Function failed after {self.config.max_attempts} attempts: {str(e)}"
                    )

        raise MaxRetriesExceeded(
            f"Max retries ({self.config.max_attempts}) exceeded",
            last_exception=last_exception,
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with optional jitter."""
        calculator = self._backoff_strategies.get(
            self.config.strategy,
            ImmediateBackoff(),
        )
        
        delay = calculator.calculate_delay(attempt, self.config)
        
        # Apply jitter
        if self.config.jitter and delay > 0:
            jitter_factor = random.uniform(
                self.config.jitter_range[0],
                self.config.jitter_range[1],
            )
            delay *= jitter_factor
        
        return delay

    def with_fallback(
        self,
        fallback_fn: Callable[..., T],
    ) -> Callable:
        """
        Create a retry executor with fallback function.
        
        If all retries fail, calls fallback_fn instead of raising.
        """
        async def wrapper(
            func: Callable,
            *args,
            **kwargs,
        ) -> T:
            try:
                return await self.execute(func, *args, **kwargs)
            except MaxRetriesExceeded:
                logger.info("All retries exhausted, using fallback")
                return await fallback_fn(*args, **kwargs)
        
        return wrapper


class RetryDecorator:
    """Decorator for adding retry logic to functions."""

    def __init__(
        self,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_attempts: int = 3,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        **config_kwargs,
    ):
        self.config = RetryConfig(
            strategy=strategy,
            max_attempts=max_attempts,
            **config_kwargs,
        )
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self.executor = RetryExecutor(self.config)

    def __call__(self, func: Callable) -> Callable:
        """Decorate async function with retry logic."""
        async def wrapper(*args, **kwargs) -> T:
            return await self.executor.execute(
                lambda: func(*args, **kwargs),
                retryable_exceptions=self.retryable_exceptions,
            )
        return wrapper


class CircuitAwareRetryExecutor(RetryExecutor):
    """Retry executor that respects circuit breaker state."""

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        circuit_breaker=None,
    ):
        super().__init__(config)
        self.circuit_breaker = circuit_breaker

    async def execute(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        **kwargs,
    ) -> T:
        """Execute with circuit breaker awareness."""
        from execution.circuit_breaker import CircuitBreakerOpen
        
        retryable_exceptions = retryable_exceptions or [Exception]
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                # Check circuit breaker before attempting
                if self.circuit_breaker:
                    result = await self.circuit_breaker.call(func, *args, **kwargs)
                else:
                    result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        f"Function succeeded on attempt {attempt + 1}/"
                        f"{self.config.max_attempts}"
                    )
                
                return result
            
            except CircuitBreakerOpen as e:
                # Circuit is open, fail fast
                logger.error(f"Circuit breaker open, failing fast: {e}")
                raise MaxRetriesExceeded(
                    "Circuit breaker open",
                    last_exception=e,
                )
            
            except BaseException as e:
                if not any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                    raise
                
                last_exception = e
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Function failed (attempt {attempt + 1}/"
                        f"{self.config.max_attempts}): {str(e)[:100]}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)

        raise MaxRetriesExceeded(
            f"Max retries ({self.config.max_attempts}) exceeded",
            last_exception=last_exception,
        )


class MaxRetriesExceeded(Exception):
    """Raised when max retries exceeded."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception
