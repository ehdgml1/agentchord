"""Math utilities for AgentWeave."""
from __future__ import annotations


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity score between -1.0 and 1.0.

    Raises:
        ValueError: If vectors have different lengths.
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have same length")

    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(x * x for x in b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)
