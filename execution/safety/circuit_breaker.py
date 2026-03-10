# circuit breaker implementation (stub)
"""Circuit breaker implementation for tool resilience"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import defaultdict

from execution.models import CircuitBreakerError


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold  # Failures before opening
        self.success_threshold = success_threshold  # Successes to close from half-open
        self.timeout_seconds = timeout_seconds  # Time before trying half-open
        self.half_open_max_calls = half_open_max_calls  # Max calls in half-open


class CircuitBreakerState:
    """State for a single circuit breaker"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.opened_at:
                elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    # Transition to half-open
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                # Close the circuit
                self._close()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed execution"""
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            # Immediately reopen on failure in half-open
            self._open()
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self._open()
    
    def _open(self):
        """Transition to open state"""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.utcnow()
        self.failure_count = 0
        self.success_count = 0
    
    def _close(self):
        """Transition to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
    
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


class CircuitBreaker:
    """Circuit breaker manager for multiple tools"""
    
    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        self.default_config = default_config or CircuitBreakerConfig()
        self._breakers: Dict[str, CircuitBreakerState] = {}
        self._configs: Dict[str, CircuitBreakerConfig] = {}
        self._lock = asyncio.Lock()
    
    def configure(self, tool_name: str, config: CircuitBreakerConfig):
        """Configure circuit breaker for specific tool"""
        self._configs[tool_name] = config
    
    def _get_breaker(self, tool_name: str) -> CircuitBreakerState:
        """Get or create circuit breaker for tool"""
        if tool_name not in self._breakers:
            config = self._configs.get(tool_name, self.default_config)
            self._breakers[tool_name] = CircuitBreakerState(config)
        return self._breakers[tool_name]
    
    async def can_execute(self, tool_name: str) -> bool:
        """Check if tool execution is allowed"""
        async with self._lock:
            breaker = self._get_breaker(tool_name)
            can_execute = breaker.can_execute()
            
            if breaker.state == CircuitState.HALF_OPEN and can_execute:
                breaker.half_open_calls += 1
            
            return can_execute
    
    async def record_success(self, tool_name: str):
        """Record successful execution"""
        async with self._lock:
            breaker = self._get_breaker(tool_name)
            breaker.record_success()
    
    async def record_failure(self, tool_name: str):
        """Record failed execution"""
        async with self._lock:
            breaker = self._get_breaker(tool_name)
            breaker.record_failure()
    
    async def reset(self, tool_name: str):
        """Reset circuit breaker for tool"""
        async with self._lock:
            if tool_name in self._breakers:
                config = self._configs.get(tool_name, self.default_config)
                self._breakers[tool_name] = CircuitBreakerState(config)
    
    def get_status(self, tool_name: Optional[str] = None) -> Dict:
        """Get circuit breaker status"""
        if tool_name:
            breaker = self._get_breaker(tool_name)
            return {tool_name: breaker.get_status()}
        
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }
    
    def get_all_open(self) -> list[str]:
        """Get all tools with open circuit breakers"""
        return [
            name
            for name, breaker in self._breakers.items()
            if breaker.state == CircuitState.OPEN
        ]