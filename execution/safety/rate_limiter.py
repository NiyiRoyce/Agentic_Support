# Rate limiting per tool
"""Rate limiting for tool executions"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import deque
import asyncio

from execution.models import RateLimitError


class RateLimitConfig:
    """Rate limit configuration"""
    
    def __init__(
        self,
        max_calls: int = 100,
        window_seconds: int = 60,
        burst_size: Optional[int] = None,
    ):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.burst_size = burst_size or max_calls


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = float(config.burst_size)
        self.last_update = datetime.utcnow()
        self._lock = asyncio.Lock()
        
        # Calculate refill rate (tokens per second)
        self.refill_rate = config.max_calls / config.window_seconds
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = datetime.utcnow()
        elapsed = (now - self.last_update).total_seconds()
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.config.burst_size, self.tokens + tokens_to_add)
        self.last_update = now
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if acquired, False if rate limited
        """
        async with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_token(self, tokens: int = 1, timeout: Optional[float] = None):
        """
        Wait until token is available
        
        Args:
            tokens: Number of tokens to wait for
            timeout: Maximum wait time in seconds
            
        Raises:
            RateLimitError if timeout exceeded
        """
        start_time = datetime.utcnow()
        
        while True:
            acquired = await self.acquire(tokens)
            if acquired:
                return
            
            if timeout:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout:
                    raise RateLimitError("Rate limit timeout exceeded")
            
            # Wait before checking again
            await asyncio.sleep(0.1)
    
    def get_status(self) -> Dict:
        """Get current rate limiter status"""
        self._refill()
        return {
            "tokens_available": self.tokens,
            "max_tokens": self.config.burst_size,
            "refill_rate": self.refill_rate,
            "last_update": self.last_update.isoformat(),
        }


class MultiRateLimiter:
    """Rate limiter manager for multiple tools"""
    
    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        self.default_config = default_config or RateLimitConfig()
        self._limiters: Dict[str, RateLimiter] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
    
    def configure(self, tool_name: str, config: RateLimitConfig):
        """Configure rate limiter for specific tool"""
        self._configs[tool_name] = config
        self._limiters[tool_name] = RateLimiter(config)
    
    def _get_limiter(self, tool_name: str) -> RateLimiter:
        """Get or create rate limiter for tool"""
        if tool_name not in self._limiters:
            config = self._configs.get(tool_name, self.default_config)
            self._limiters[tool_name] = RateLimiter(config)
        return self._limiters[tool_name]
    
    async def acquire(self, tool_name: str, tokens: int = 1) -> bool:
        """Try to acquire tokens for tool"""
        limiter = self._get_limiter(tool_name)
        return await limiter.acquire(tokens)
    
    async def wait_for_token(
        self,
        tool_name: str,
        tokens: int = 1,
        timeout: Optional[float] = None,
    ):
        """Wait for token availability"""
        limiter = self._get_limiter(tool_name)
        await limiter.wait_for_token(tokens, timeout)
    
    def get_status(self, tool_name: Optional[str] = None) -> Dict:
        """Get rate limiter status"""
        if tool_name:
            limiter = self._get_limiter(tool_name)
            return {tool_name: limiter.get_status()}
        
        return {
            name: limiter.get_status()
            for name, limiter in self._limiters.items()
        }