"""Anthropic (Claude) LLM provider implementation."""

from typing import List, Optional
from anthropic import AsyncAnthropic, AnthropicError

from llm.providers.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMProvider,
)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""

    # Pricing per 1M tokens
    PRICING = {
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    }

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-5-20250929"):
        super().__init__(api_key, default_model)
        self.client = AsyncAnthropic(api_key=api_key)
        self.provider_name = LLMProvider.ANTHROPIC

    async def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate completion using Anthropic Claude."""
        cfg = self._create_default_config(config)

        try:
            # Separate system message from conversation
            system_message = None
            conversation_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    conversation_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Build request params
            params = {
                "model": cfg.model,
                "messages": conversation_messages,
                "max_tokens": cfg.max_tokens,
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "timeout": cfg.timeout,
            }

            if system_message:
                params["system"] = system_message

            if cfg.stop_sequences:
                params["stop_sequences"] = cfg.stop_sequences

            # Make API call
            response = await self.client.messages.create(**params)

            # Extract usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens

            # Calculate cost
            cost = self._calculate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=cfg.model,
            )

            # Extract content
            content = ""
            if response.content:
                content = response.content[0].text

            return LLMResponse(
                content=content,
                model=cfg.model,
                provider=self.provider_name,
                tokens_used=tokens_used,
                cost_usd=cost,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "stop_reason": response.stop_reason,
                },
                success=True,
            )

        except AnthropicError as e:
            return LLMResponse(
                content="",
                model=cfg.model,
                provider=self.provider_name,
                tokens_used=0,
                cost_usd=0.0,
                metadata={"error_type": type(e).__name__},
                success=False,
                error=str(e),
            )

        except Exception as e:
            return LLMResponse(
                content="",
                model=cfg.model,
                provider=self.provider_name,
                tokens_used=0,
                cost_usd=0.0,
                metadata={"error_type": "unexpected"},
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

    def _calculate_cost(
        self, input_tokens: int, output_tokens: int, model: str
    ) -> float:
        """Calculate cost based on token usage."""
        pricing = self.PRICING.get(model)
        if not pricing:
            # Default to Sonnet pricing if model not found
            pricing = self.PRICING["claude-sonnet-4-5-20250929"]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for given token count."""
        pricing = self.PRICING.get(model, self.PRICING["claude-sonnet-4-5-20250929"])
        # Assume 50/50 split between input and output
        return (tokens / 1_000_000) * (pricing["input"] + pricing["output"]) / 2

    def count_tokens(self, text: str, model: str) -> int:
        """
        Approximate token count for Claude.
        Claude uses ~4 characters per token on average.
        """
        return len(text) // 4