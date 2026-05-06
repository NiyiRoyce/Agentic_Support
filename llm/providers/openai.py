"""OpenAI LLM provider implementation."""

from typing import List, Optional, Any, Dict, cast
import tiktoken
from openai import AsyncOpenAI, OpenAIError

from llm.providers.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMProvider,
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    # Pricing per 1M tokens
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"):
        super().__init__(api_key, default_model)
        self.client = AsyncOpenAI(api_key=api_key)
        self.provider_name = LLMProvider.OPENAI

    async def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate completion using OpenAI."""
        cfg = self._create_default_config(config)

        try:
            # Convert messages to OpenAI-compatible format
            openai_messages = cast(
                List[Dict[str, str]],
                [{"role": msg.role, "content": msg.content} for msg in messages],
            )

            # Build kwargs safely (avoid passing None)
            kwargs: Dict[str, Any] = {
                "model": cfg.model,
                "messages": openai_messages,
            }

            if cfg.temperature is not None:
                kwargs["temperature"] = cfg.temperature

            if cfg.max_tokens is not None:
                kwargs["max_tokens"] = cfg.max_tokens

            if cfg.top_p is not None:
                kwargs["top_p"] = cfg.top_p

            if cfg.frequency_penalty is not None:
                kwargs["frequency_penalty"] = cfg.frequency_penalty

            if cfg.presence_penalty is not None:
                kwargs["presence_penalty"] = cfg.presence_penalty

            if cfg.timeout is not None:
                kwargs["timeout"] = cfg.timeout

            if cfg.stop_sequences:
                kwargs["stop"] = cfg.stop_sequences

            if cfg.json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            # API call
            response = await self.client.chat.completions.create(**kwargs)

            # Extract usage safely
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            tokens_used = usage.total_tokens if usage else 0

            # Calculate cost
            cost = self._calculate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=cfg.model,
            )

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=cfg.model,
                provider=self.provider_name,
                tokens_used=tokens_used,
                cost_usd=cost,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "finish_reason": response.choices[0].finish_reason,
                },
                success=True,
            )

        except OpenAIError as e:
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
        pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for given token count."""
        pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])
        return (tokens / 1_000_000) * (pricing["input"] + pricing["output"]) / 2

    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens using tiktoken."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))
