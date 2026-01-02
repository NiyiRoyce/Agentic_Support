"""OpenAI LLM provider implementation."""

import asyncio
from typing import List, Optional
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

    # Pricing per 1M tokens (as of 2024)
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
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Build request params
            params = {
                "model": cfg.model,
                "messages": openai_messages,
                "temperature": cfg.temperature,
                "max_tokens": cfg.max_tokens,
                "top_p": cfg.top_p,
                "frequency_penalty": cfg.frequency_penalty,
                "presence_penalty": cfg.presence_penalty,
                "timeout": cfg.timeout,
            }

            if cfg.stop_sequences:
                params["stop"] = cfg.stop_sequences

            if cfg.json_mode:
                params["response_format"] = {"type": "json_object"}

            # Make API call
            response = await self.client.chat.completions.create(**params)

            # Extract usage
            usage = response.usage
            tokens_used = usage.total_tokens
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens

            # Calculate cost
            cost = self._calculate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=cfg.model,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
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
        pricing = self.PRICING.get(model)
        if not pricing:
            # Default to gpt-4o pricing if model not found
            pricing = self.PRICING["gpt-4o"]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for given token count."""
        pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])
        # Assume 50/50 split between input and output
        return (tokens / 1_000_000) * (pricing["input"] + pricing["output"]) / 2

    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens using tiktoken."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Default to cl100k_base for unknown models
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))