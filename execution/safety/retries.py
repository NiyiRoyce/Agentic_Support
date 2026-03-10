# retry helpers
"""Retry strategies with exponential backoff"""
from typing import Callable, Any, Optional, Type, Tuple
import asyncio
from datetime import datetime
import random
import logging

from execution.models import ToolError

logger = logging.getLogger(__name__)


class RetryConfig:
    """Retry configuration"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        self.max_attempts = max_attempts
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (Exception,)


class RetryStrategy:
    """Retry strategy with exponential backoff"""
    
    def __init__(self, default_config: Optional[RetryConfig] = None):
        self.default_config = default_config or RetryConfig()
        self._tool_configs: dict[str, RetryConfig] = {}
    
    def configure(self, tool_name: str, config: RetryConfig):
        """Configure retry strategy for specific tool"""
        self._tool_configs[tool_name] = config
    
    def _get_config(self, tool_name: Optional[str] = None) -> RetryConfig:
        """Get config for tool"""
        if tool_name and tool_name in self._tool_configs:
            return self._tool_configs[tool_name]
        return self.default_config
    
    def _calculate_delay(
        self,
        attempt: int,
        config: RetryConfig,
    ) -> float:
        """Calculate delay for attempt with exponential backoff"""
        delay = config.initial_delay_seconds * (config.exponential_base ** attempt)
        delay = min(delay, config.max_delay_seconds)
        
        if config.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def _is_retryable(
        self,
        exception: Exception,
        config: RetryConfig,
    ) -> bool:
        """Check if exception is retryable"""
        return isinstance(exception, config.retryable_exceptions)
    
    async def execute(
        self,
        func: Callable,
        *args,
        tool_name: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            tool_name: Tool name for config lookup
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            Last exception if all retries exhausted
        """
        config = self._get_config(tool_name)
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        f"Retry succeeded for {tool_name or 'unknown'} "
                        f"on attempt {attempt + 1}/{config.max_attempts}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self._is_retryable(e, config):
                    logger.warning(
                        f"Non-retryable exception for {tool_name or 'unknown'}: {e}"
                    )
                    raise
                
                # Check if we have more attempts
                if attempt >= config.max_attempts - 1:
                    logger.error(
                        f"All retry attempts exhausted for {tool_name or 'unknown'}: {e}"
                    )
                    raise
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt, config)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{config.max_attempts} "
                    f"for {tool_name or 'unknown'} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic failed unexpectedly")
    
    async def execute_with_result(
        self,
        func: Callable,
        *args,
        tool_name: Optional[str] = None,
        **kwargs,
    ) -> Tuple[Any, int]:
        """
        Execute with retry and return result + attempt count
        
        Returns:
            Tuple of (result, attempt_count)
        """
        config = self._get_config(tool_name)
        
        for attempt in range(config.max_attempts):
            try:
                result = await func(*args, **kwargs)
                return result, attempt + 1
            except Exception as e:
                if not self._is_retryable(e, config) or attempt >= config.max_attempts - 1:
                    raise
                
                delay = self._calculate_delay(attempt, config)
                await asyncio.sleep(delay)
        
        raise RuntimeError("Retry logic failed unexpectedly")