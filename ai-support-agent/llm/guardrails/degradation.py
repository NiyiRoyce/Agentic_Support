# degradation strategies
"""Graceful degradation strategies for LLM failures."""

from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
import time


class DegradationLevel(str, Enum):
    """Levels of service degradation."""
    FULL = "full"  # Full LLM capabilities
    REDUCED = "reduced"  # Limited LLM with more constraints
    FALLBACK = "fallback"  # Template-based responses
    MINIMAL = "minimal"  # Basic keyword matching
    OFFLINE = "offline"  # System unavailable message


@dataclass
class DegradationConfig:
    """Configuration for graceful degradation."""
    failure_threshold: int = 3  # Failures before degrading
    recovery_threshold: int = 2  # Successes before upgrading
    degradation_timeout: int = 300  # Seconds before attempting recovery
    
    # Enable/disable specific degradation levels
    enable_reduced: bool = True
    enable_fallback: bool = True
    enable_minimal: bool = True


@dataclass
class DegradationState:
    """Current degradation state."""
    level: DegradationLevel
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    metadata: Dict[str, Any]


class GracefulDegradation:
    """
    Manages graceful degradation of LLM service quality.
    Automatically degrades and recovers based on failure patterns.
    """

    def __init__(self, config: Optional[DegradationConfig] = None):
        self.config = config or DegradationConfig()
        self.state = DegradationState(
            level=DegradationLevel.FULL,
            failure_count=0,
            success_count=0,
            last_failure_time=None,
            last_success_time=None,
            metadata={},
        )
        
        # Fallback response templates
        self._fallback_templates = self._initialize_fallback_templates()
        
        # Keyword-based minimal responses
        self._keyword_responses = self._initialize_keyword_responses()

    def _initialize_fallback_templates(self) -> Dict[str, str]:
        """Initialize template-based fallback responses."""
        return {
            "greeting": "Hello! I'm here to help you today. How can I assist you?",
            "order_status": "I can help you check your order status. Please provide your order number.",
            "product_info": "I'd be happy to provide product information. What product are you interested in?",
            "ticket_creation": "I'll create a support ticket for you. Please describe your issue in detail.",
            "escalation": "I'm connecting you with a human agent who can better assist you. Please wait a moment.",
            "error": "I'm experiencing technical difficulties. Please try again in a few moments or contact support@example.com",
            "unknown": "I'm here to help! Could you please rephrase your question or tell me more about what you need?",
        }

    def _initialize_keyword_responses(self) -> Dict[str, List[tuple]]:
        """Initialize keyword-based minimal responses."""
        return {
            "order": [
                (["order", "tracking", "delivery", "shipped"], 
                 "To check your order status, please visit our order tracking page or contact support with your order number."),
                (["cancel", "return", "refund"],
                 "For cancellations, returns, or refunds, please contact our support team at support@example.com"),
            ],
            "product": [
                (["price", "cost", "how much"],
                 "For current pricing, please visit our website or contact our sales team."),
                (["available", "stock", "in stock"],
                 "To check product availability, please visit our website or contact support."),
            ],
            "account": [
                (["login", "password", "reset"],
                 "For login or password issues, please use the 'Forgot Password' link on the login page."),
                (["account", "profile", "settings"],
                 "To manage your account, please log in to your dashboard."),
            ],
            "general": [
                (["help", "support", "assist"],
                 "I'm here to help! Please describe your issue and I'll do my best to assist you."),
                (["thank", "thanks"],
                 "You're welcome! Let me know if you need anything else."),
            ],
        }

    async def execute(
        self,
        func: Callable,
        intent: str = "unknown",
        user_message: str = "",
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with graceful degradation.
        """
        # Check if we should attempt recovery
        self._check_recovery_opportunity()

        # Execute based on current degradation level
        if self.state.level == DegradationLevel.FULL:
            return await self._execute_full(func, intent, user_message, *args, **kwargs)
        
        elif self.state.level == DegradationLevel.REDUCED:
            return await self._execute_reduced(func, intent, user_message, *args, **kwargs)
        
        elif self.state.level == DegradationLevel.FALLBACK:
            return self._execute_fallback(intent, user_message)
        
        elif self.state.level == DegradationLevel.MINIMAL:
            return self._execute_minimal(user_message)
        
        else:  # OFFLINE
            return self._execute_offline()

    async def _execute_full(
        self,
        func: Callable,
        intent: str,
        user_message: str,
        *args,
        **kwargs,
    ) -> Any:
        """Execute with full LLM capabilities."""
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            
            # If degraded, use fallback
            if self.state.level != DegradationLevel.FULL:
                return await self.execute(func, intent, user_message, *args, **kwargs)
            raise e

    async def _execute_reduced(
        self,
        func: Callable,
        intent: str,
        user_message: str,
        *args,
        **kwargs,
    ) -> Any:
        """Execute with reduced LLM capabilities (shorter timeouts, simpler prompts)."""
        try:
            # Modify kwargs to use reduced capabilities
            if 'config' in kwargs and hasattr(kwargs['config'], 'max_tokens'):
                kwargs['config'].max_tokens = min(kwargs['config'].max_tokens, 500)
                kwargs['config'].timeout = 15  # Shorter timeout

            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            
            # If further degraded, use fallback
            if self.state.level != DegradationLevel.REDUCED:
                return await self.execute(func, intent, user_message, *args, **kwargs)
            
            # Otherwise return fallback directly
            return self._execute_fallback(intent, user_message)

    def _execute_fallback(self, intent: str, user_message: str) -> Dict[str, Any]:
        """Execute with template-based fallback."""
        template = self._fallback_templates.get(intent, self._fallback_templates["unknown"])
        
        return {
            "content": template,
            "degraded": True,
            "degradation_level": DegradationLevel.FALLBACK.value,
            "metadata": {
                "used_template": True,
                "intent": intent,
            }
        }

    def _execute_minimal(self, user_message: str) -> Dict[str, Any]:
        """Execute with minimal keyword-based matching."""
        message_lower = user_message.lower()
        
        # Try to match keywords
        for category, patterns in self._keyword_responses.items():
            for keywords, response in patterns:
                if any(keyword in message_lower for keyword in keywords):
                    return {
                        "content": response,
                        "degraded": True,
                        "degradation_level": DegradationLevel.MINIMAL.value,
                        "metadata": {
                            "matched_category": category,
                            "matched_keywords": keywords,
                        }
                    }
        
        # No match found
        return {
            "content": self._fallback_templates["unknown"],
            "degraded": True,
            "degradation_level": DegradationLevel.MINIMAL.value,
            "metadata": {
                "no_match": True,
            }
        }

    def _execute_offline(self) -> Dict[str, Any]:
        """Execute in offline mode."""
        return {
            "content": self._fallback_templates["error"],
            "degraded": True,
            "degradation_level": DegradationLevel.OFFLINE.value,
            "metadata": {
                "system_offline": True,
            }
        }

    def _record_success(self):
        """Record successful execution."""
        self.state.success_count += 1
        self.state.failure_count = 0
        self.state.last_success_time = time.time()

        # Check if we should upgrade
        if self.state.success_count >= self.config.recovery_threshold:
            self._upgrade_service_level()

    def _record_failure(self):
        """Record failed execution."""
        self.state.failure_count += 1
        self.state.success_count = 0
        self.state.last_failure_time = time.time()

        # Check if we should degrade
        if self.state.failure_count >= self.config.failure_threshold:
            self._degrade_service_level()

    def _degrade_service_level(self):
        """Degrade to next lower service level."""
        if self.state.level == DegradationLevel.FULL and self.config.enable_reduced:
            self.state.level = DegradationLevel.REDUCED
        elif self.state.level in [DegradationLevel.FULL, DegradationLevel.REDUCED] and self.config.enable_fallback:
            self.state.level = DegradationLevel.FALLBACK
        elif self.state.level in [DegradationLevel.FULL, DegradationLevel.REDUCED, DegradationLevel.FALLBACK] and self.config.enable_minimal:
            self.state.level = DegradationLevel.MINIMAL
        else:
            self.state.level = DegradationLevel.OFFLINE

        self.state.failure_count = 0
        self.state.metadata["degraded_at"] = time.time()

    def _upgrade_service_level(self):
        """Upgrade to next higher service level."""
        if self.state.level == DegradationLevel.OFFLINE:
            self.state.level = DegradationLevel.MINIMAL
        elif self.state.level == DegradationLevel.MINIMAL:
            self.state.level = DegradationLevel.FALLBACK
        elif self.state.level == DegradationLevel.FALLBACK:
            self.state.level = DegradationLevel.REDUCED
        elif self.state.level == DegradationLevel.REDUCED:
            self.state.level = DegradationLevel.FULL

        self.state.success_count = 0
        self.state.metadata["upgraded_at"] = time.time()

    def _check_recovery_opportunity(self):
        """Check if enough time has passed to attempt recovery."""
        if self.state.level == DegradationLevel.FULL:
            return

        if self.state.last_failure_time:
            time_since_failure = time.time() - self.state.last_failure_time
            
            if time_since_failure >= self.config.degradation_timeout:
                # Attempt to upgrade one level
                self._upgrade_service_level()

    def get_state(self) -> Dict[str, Any]:
        """Get current degradation state for monitoring."""
        return {
            "level": self.state.level.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "last_failure_time": self.state.last_failure_time,
            "last_success_time": self.state.last_success_time,
            "is_degraded": self.state.level != DegradationLevel.FULL,
            "metadata": self.state.metadata,
        }

    def force_level(self, level: DegradationLevel):
        """Manually set degradation level (for testing or emergency)."""
        self.state.level = level
        self.state.failure_count = 0
        self.state.success_count = 0
        self.state.metadata["manually_set"] = True

    def reset(self):
        """Reset to full service level."""
        self.state = DegradationState(
            level=DegradationLevel.FULL,
            failure_count=0,
            success_count=0,
            last_failure_time=None,
            last_success_time=None,
            metadata={},
        )