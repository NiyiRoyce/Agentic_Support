"""LLM cost tracking utilities."""

from typing import Dict, Optional, Any
from observability.metrics import increment_llm_cost, increment_llm_token_count
import logging

logger = logging.getLogger(__name__)

# Cost per 1K tokens (USD) - approximate rates, update as needed
COST_RATES = {
    "openai": {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    },
    "anthropic": {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }
}


def calculate_llm_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost of an LLM request.

    Args:
        provider: LLM provider (openai, anthropic)
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    rates = COST_RATES.get(provider, {}).get(model, {})
    if not rates:
        logger.warning(f"No cost rates found for {provider}/{model}, using zero cost")
        return 0.0

    input_cost = (input_tokens / 1000) * rates.get("input", 0)
    output_cost = (output_tokens / 1000) * rates.get("output", 0)
    total_cost = input_cost + output_cost

    return total_cost


def track_llm_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> None:
    """
    Track LLM cost and update metrics.

    Args:
        provider: LLM provider
        model: Model name
        input_tokens: Input token count
        output_tokens: Output token count
    """
    cost = calculate_llm_cost(provider, model, input_tokens, output_tokens)

    # Update metrics
    increment_llm_token_count(provider, model, "input", input_tokens)
    increment_llm_token_count(provider, model, "output", output_tokens)
    increment_llm_cost(provider, model, cost)

    logger.info(
        "LLM cost tracked",
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost
    )


def extract_tokens_from_response(response: Any) -> tuple[int, int]:
    """
    Extract token counts from LLM response.

    Args:
        response: LLM response object

    Returns:
        Tuple of (input_tokens, output_tokens)
    """
    # This depends on the LLM provider response structure
    # For OpenAI: response.usage.prompt_tokens, response.usage.completion_tokens
    # For Anthropic: response.usage.input_tokens, response.usage.output_tokens

    input_tokens = getattr(response, 'usage', {}).get('prompt_tokens', 0) or \
                  getattr(response, 'usage', {}).get('input_tokens', 0)
    output_tokens = getattr(response, 'usage', {}).get('completion_tokens', 0) or \
                   getattr(response, 'usage', {}).get('output_tokens', 0)

    return input_tokens, output_tokens


def track_llm_response(provider: str, model: str, response: Any) -> None:
    """
    Track cost and metrics from LLM response.

    Args:
        provider: LLM provider
        model: Model name
        response: LLM response object (LLMResponse or raw response)
    """
    # Try to extract from LLMResponse first
    if hasattr(response, 'tokens_used'):
        # Assume input_tokens is not separated, use total tokens for cost estimation
        # In practice, you'd want input/output separated
        input_tokens = response.tokens_used // 2  # Rough estimate
        output_tokens = response.tokens_used // 2
    else:
        # Fallback to extracting from raw response
        input_tokens, output_tokens = extract_tokens_from_response(response)
    
    track_llm_cost(provider, model, input_tokens, output_tokens)
