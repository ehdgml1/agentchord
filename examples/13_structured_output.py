"""Example 12: Structured Output with JSON Schemas.

This example demonstrates how to use OutputSchema to get validated,
structured JSON responses from LLMs conforming to Pydantic models.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel, Field

# Mock provider for demonstration (replace with real provider)
from agentweave import Agent
from agentweave.core.structured import OutputSchema
from agentweave.core.types import LLMResponse, Message, Usage
from agentweave.llm.base import BaseLLMProvider


class SentimentAnalysis(BaseModel):
    """Analysis of text sentiment."""

    sentiment: Literal["positive", "negative", "neutral"] = Field(
        ..., description="Overall sentiment of the text"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    key_phrases: list[str] = Field(
        ..., description="Important phrases that influenced the sentiment"
    )
    summary: str = Field(..., description="Brief explanation of the analysis")


class ProductRecommendations(BaseModel):
    """Product recommendations based on user preferences."""

    recommendations: list[str] = Field(
        ..., min_length=1, max_length=5, description="List of recommended products"
    )
    reasoning: str = Field(..., description="Why these products were recommended")
    confidence_level: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in these recommendations"
    )


class MockStructuredProvider(BaseLLMProvider):
    """Mock provider that simulates structured JSON responses."""

    @property
    def model(self) -> str:
        return "mock-structured"

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0

    async def complete(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        # Simulate different responses based on the request
        content = messages[-1].content.lower()

        if "review" in content or "analyze" in content:
            response = """{
                "sentiment": "positive",
                "confidence": 0.92,
                "key_phrases": ["amazing quality", "great value", "highly recommend"],
                "summary": "Customer is very satisfied with the product quality and value."
            }"""
        elif "recommend" in content or "tech" in content:
            response = """{
                "recommendations": ["Wireless Headphones", "Smart Watch", "Portable Charger"],
                "reasoning": "Based on tech preferences and portability needs",
                "confidence_level": "high"
            }"""
        else:
            response = "{}"

        return LLMResponse(
            content=response,
            model="mock-structured",
            usage=Usage(prompt_tokens=50, completion_tokens=100),
            finish_reason="stop",
        )

    async def stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        raise NotImplementedError("Stream not used in this example")


async def example_sentiment_analysis() -> None:
    """Example: Analyze sentiment with structured output."""
    print("=== Example 1: Sentiment Analysis with Structured Output ===\n")

    # Create agent with mock provider
    agent = Agent(
        name="sentiment-analyzer",
        role="Analyzes text sentiment and provides structured insights",
        llm_provider=MockStructuredProvider(),
    )

    # Define output schema
    schema = OutputSchema(
        SentimentAnalysis,
        description="Structured sentiment analysis result",
    )

    # Run agent with schema
    result = await agent.run(
        "Analyze this review: 'This product is amazing! Great quality and value.'",
        output_schema=schema,
    )

    # The raw JSON response
    print("Raw LLM Response:")
    print(result.output)
    print()

    # The parsed and validated output
    if result.parsed_output:
        print("Parsed & Validated Output:")
        print(f"  Sentiment: {result.parsed_output['sentiment']}")
        print(f"  Confidence: {result.parsed_output['confidence']:.2%}")
        print(f"  Key Phrases: {', '.join(result.parsed_output['key_phrases'])}")
        print(f"  Summary: {result.parsed_output['summary']}")
    else:
        print("Failed to parse output")

    print()


async def example_product_recommendations() -> None:
    """Example: Get product recommendations with structured output."""
    print("=== Example 2: Product Recommendations with Structured Output ===\n")

    agent = Agent(
        name="product-recommender",
        role="Recommends products based on user preferences",
        llm_provider=MockStructuredProvider(),
    )

    schema = OutputSchema(
        ProductRecommendations,
        description="Structured product recommendations",
    )

    result = await agent.run(
        "Recommend tech products for someone who travels frequently",
        output_schema=schema,
    )

    print("Raw LLM Response:")
    print(result.output)
    print()

    if result.parsed_output:
        print("Parsed & Validated Output:")
        print(f"  Recommendations:")
        for i, product in enumerate(result.parsed_output["recommendations"], 1):
            print(f"    {i}. {product}")
        print(f"  Reasoning: {result.parsed_output['reasoning']}")
        print(f"  Confidence: {result.parsed_output['confidence_level']}")
    else:
        print("Failed to parse output")

    print()


async def example_with_real_provider() -> None:
    """Example: Using structured output with real OpenAI provider."""
    print("=== Example 3: Using with Real Provider (OpenAI) ===\n")
    print("To use with a real provider, replace MockStructuredProvider with:")
    print()
    print("  from agentweave.llm.openai import OpenAIProvider")
    print()
    print("  agent = Agent(")
    print('      name="analyzer",')
    print('      role="Sentiment analyzer",')
    print('      model="gpt-4o-mini",')
    print("      # OpenAI provider will be auto-detected from model name")
    print("  )")
    print()
    print("  schema = OutputSchema(SentimentAnalysis)")
    print('  result = await agent.run("Analyze this...", output_schema=schema)')
    print()
    print(
        "OpenAI's native JSON schema mode will be used automatically for strict validation."
    )
    print()


async def example_error_handling() -> None:
    """Example: Handling validation errors gracefully."""
    print("=== Example 4: Error Handling ===\n")
    print("If the LLM returns invalid JSON or doesn't match the schema:")
    print("  - result.parsed_output will be None")
    print("  - result.output will still contain the raw response")
    print("  - You can handle this gracefully:")
    print()
    print("  if result.parsed_output:")
    print("      # Use the validated, typed data")
    print("      sentiment = result.parsed_output['sentiment']")
    print("  else:")
    print("      # Fallback or retry logic")
    print("      print('Failed to parse. Raw output:', result.output)")
    print()


async def main() -> None:
    """Run all structured output examples."""
    await example_sentiment_analysis()
    await example_product_recommendations()
    await example_with_real_provider()
    await example_error_handling()

    print("=== Key Benefits of Structured Output ===")
    print("1. Type Safety: Validated Pydantic models ensure data integrity")
    print("2. Auto-completion: IDEs can suggest fields from the schema")
    print("3. OpenAI Native: Uses OpenAI's strict JSON schema mode when available")
    print("4. Graceful Fallback: Other providers get schema in system prompt")
    print("5. Error Handling: validate_safe() prevents crashes on malformed JSON")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
