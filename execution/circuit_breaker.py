"""Circuit breaker pattern implementation for execution resilience.

Prevents cascading failures by tracking provider/service health and temporarily
disabling failing services to allow recovery.
"""

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, TypeVar, Generic, Dict, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests rejected immediately
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Seconds before attempting recovery from open state
    window_size: int = 100  # Number of requests to track for failure rate


@dataclass
class CircuitBreakerMetrics:
    """Metrics collected by circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: Dict[CircuitState, int] = field(default_factory=lambda: {
        CircuitState.CLOSED: 0,
        CircuitState.OPEN: 0,
        CircuitState.HALF_OPEN: 0,
    })


class CircuitBreaker(Generic[T]):
    """
    Circuit breaker pattern implementation.
    
    Protects against cascading failures by monitoring success/failure rates
    and temporarily disabling failing services.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._state_lock = asyncio.Lock()
        self._failure_stack: list[float] = []  # Timestamps of recent failures
        self._half_open_successes = 0
        self._last_state_change = datetime.utcnow()

    async def call(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from function
            
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        async with self._state_lock:
            await self._check_state_transition()
            
            if self.state == CircuitState.OPEN:
                self.metrics.rejected_calls += 1
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is OPEN"
                )

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise

    async def _check_state_transition(self) -> None:
        """Check and transition circuit state if needed."""
        if self.state == CircuitState.CLOSED:
            # Check if we should open
            if self._should_open():
                await self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker '{self.name}' opened after "
                    f"{self.config.failure_threshold} failures"
                )
        
        elif self.state == CircuitState.OPEN:
            # Check if we should attempt half-open
            if self._should_attempt_half_open():
                await self._transition_to(CircuitState.HALF_OPEN)
                self._half_open_successes = 0
                logger.info(
                    f"Circuit breaker '{self.name}' entering HALF_OPEN state"
                )
        
        elif self.state == CircuitState.HALF_OPEN:
            # Check if we should fully close (recovery successful)
            if self._half_open_successes >= self.config.success_threshold:
                await self._transition_to(CircuitState.CLOSED)
                self._failure_stack.clear()
                logger.info(
                    f"Circuit breaker '{self.name}' CLOSED after successful recovery"
                )

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            self._last_state_change = datetime.utcnow()
            self.metrics.state_changes[new_state] += 1
            logger.info(
                f"Circuit breaker '{self.name}': {old_state} -> {new_state}"
            )

    def _should_open(self) -> bool:
        """Check if circuit should open."""
        if len(self._failure_stack) < self.config.failure_threshold:
            return False
        
        # Check if failures are recent (within window)
        now = datetime.utcnow()
        recent_failures = sum(
            1 for ts in self._failure_stack
            if (now - datetime.fromtimestamp(ts)).total_seconds() <= self.config.timeout
        )
        
        return recent_failures >= self.config.failure_threshold

    def _should_attempt_half_open(self) -> bool:
        """Check if circuit should transition to half-open."""
        if self.state != CircuitState.OPEN:
            return False
        
        time_since_open = (
            datetime.utcnow() - self._last_state_change
        ).total_seconds()
        return time_since_open >= self.config.timeout

    async def _record_success(self) -> None:
        """Record successful call."""
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
        
        async with self._state_lock:
            await self._check_state_transition()

    async def _record_failure(self) -> None:
        """Record failed call."""
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = datetime.utcnow()
        
        # Add current timestamp to failure stack
        self._failure_stack.append(datetime.utcnow().timestamp())
        
        # Keep only recent failures within window
        now = datetime.utcnow()
        self._failure_stack = [
            ts for ts in self._failure_stack
            if (now - datetime.fromtimestamp(ts)).total_seconds() <= self.config.timeout * 2
        ]
        
        async with self._state_lock:
            await self._check_state_transition()

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit metrics."""
        return self.metrics

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        self.state = CircuitState.CLOSED
        self._failure_stack.clear()
        self._half_open_successes = 0
        self.metrics = CircuitBreakerMetrics()
        logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        async with self._lock:
            if name not in self.breakers:
                self.breakers[name] = CircuitBreaker(name, config)
            return self.breakers[name]

    async def call(
        self,
        breaker_name: str,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """Call function through circuit breaker."""
        breaker = await self.get_or_create(breaker_name)
        return await breaker.call(func, *args, **kwargs)

    def get_all_metrics(self) -> Dict[str, CircuitBreakerMetrics]:
        """Get metrics from all circuit breakers."""
        return {
            name: breaker.get_metrics()
            for name, breaker in self.breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass
