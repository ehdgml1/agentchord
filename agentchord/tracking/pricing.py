"""Model pricing information."""

from __future__ import annotations

from agentchord.tracking.models import TokenUsage


# Pricing per 1 million tokens: (input_price, output_price)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI models
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-2024-08-06": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4-turbo-preview": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    # Anthropic models
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
    "claude-3-opus-20240229": (15.00, 75.00),
    "claude-3-opus-latest": (15.00, 75.00),
    "claude-3-sonnet-20240229": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
    # Aliases for convenience
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-haiku": (0.25, 1.25),
}

# Default pricing for unknown models
DEFAULT_PRICING: tuple[float, float] = (1.00, 2.00)


def get_model_pricing(model: str) -> tuple[float, float]:
    """Get pricing for a model.

    Args:
        model: Model name or ID.

    Returns:
        Tuple of (input_price, output_price) per 1M tokens.
    """
    # Try exact match first
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Try prefix matching for versioned models
    model_lower = model.lower()
    for known_model, pricing in MODEL_PRICING.items():
        if model_lower.startswith(known_model.lower()):
            return pricing

    return DEFAULT_PRICING


def calculate_cost(model: str, usage: TokenUsage) -> float:
    """Calculate cost in USD for token usage.

    Args:
        model: Model name.
        usage: Token usage.

    Returns:
        Cost in USD.
    """
    input_price, output_price = get_model_pricing(model)

    # Convert from per-1M to actual cost
    input_cost = (usage.prompt_tokens / 1_000_000) * input_price
    output_cost = (usage.completion_tokens / 1_000_000) * output_price

    return input_cost + output_cost
