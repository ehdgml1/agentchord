"""RAG evaluation metrics using LLM-as-a-Judge.

Self-implemented RAGAS-style metrics for evaluating RAG quality:
    - Faithfulness: Is the answer grounded in the context?
    - Answer Relevancy: Does the answer address the question?
    - Context Relevancy: Is the retrieved context relevant to the query?
    - RAGAS Score: Harmonic mean of all metrics.

Each metric uses an LLM to judge quality on a 0-1 scale.
No external evaluation libraries required.

Reference:
    Es, Shahul et al. (2023). "RAGAS: Automated Evaluation of
    Retrieval Augmented Generation"
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agentweave.core.types import Message, MessageRole
from agentweave.llm.base import BaseLLMProvider


@dataclass
class MetricResult:
    """Result from a single metric evaluation."""

    name: str
    score: float
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class BaseMetric(ABC):
    """Abstract base for RAG evaluation metrics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Metric name."""

    @abstractmethod
    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> MetricResult:
        """Evaluate the metric.

        Args:
            query: Original user question.
            answer: Generated answer.
            contexts: Retrieved context strings.

        Returns:
            MetricResult with score (0-1) and reasoning.
        """


class Faithfulness(BaseMetric):
    """Measures if the answer is factually grounded in the context.

    A faithful answer only contains claims that can be verified
    from the provided context. Hallucinated claims reduce the score.

    Score interpretation:
        1.0: Fully faithful — all claims supported by context
        0.5: Partially faithful — some claims unsupported
        0.0: Unfaithful — answer contradicts or fabricates beyond context
    """

    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "faithfulness"

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> MetricResult:
        context_str = "\n---\n".join(contexts)

        # Step 1: Extract claims from the answer
        extract_prompt = (
            "Extract all factual claims from the following answer. "
            "List each claim on a separate line, prefixed with '- '.\n\n"
            f"Answer: {answer}\n\n"
            "Claims:"
        )
        extract_response = await self._llm.complete(
            [Message(role=MessageRole.USER, content=extract_prompt)],
            temperature=0.0,
            max_tokens=512,
        )

        claims = [
            line.strip().lstrip("- ").strip()
            for line in extract_response.content.strip().split("\n")
            if line.strip().startswith("-") or line.strip().startswith("•")
        ]

        if not claims:
            return MetricResult(
                name=self.name,
                score=1.0,
                reason="No factual claims found in answer.",
            )

        # Step 2: Verify each claim against context
        verify_prompt = (
            "For each claim below, determine if it is SUPPORTED by the context.\n"
            "Respond with 'SUPPORTED' or 'NOT SUPPORTED' for each claim.\n\n"
            f"Context:\n{context_str}\n\n"
            "Claims:\n"
            + "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
            + "\n\nVerdict for each (one per line):"
        )

        verify_response = await self._llm.complete(
            [Message(role=MessageRole.USER, content=verify_prompt)],
            temperature=0.0,
            max_tokens=256,
        )

        supported = sum(
            1
            for line in verify_response.content.upper().split("\n")
            if "SUPPORTED" in line and "NOT SUPPORTED" not in line
        )

        score = supported / len(claims) if claims else 1.0

        return MetricResult(
            name=self.name,
            score=round(score, 4),
            reason=f"{supported}/{len(claims)} claims supported by context.",
            details={"claims": claims, "supported_count": supported},
        )


class AnswerRelevancy(BaseMetric):
    """Measures if the answer addresses the original question.

    An answer is relevant if it directly addresses the question
    without excessive tangential information.

    Score interpretation:
        1.0: Directly answers the question
        0.5: Partially relevant or too broad
        0.0: Completely irrelevant to the question
    """

    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "answer_relevancy"

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> MetricResult:
        prompt = (
            "Rate how well the answer addresses the question on a scale of 0 to 10.\n\n"
            "Criteria:\n"
            "- Does the answer directly address the question?\n"
            "- Is the answer complete without being excessive?\n"
            "- Does the answer stay on topic?\n\n"
            f"Question: {query}\n"
            f"Answer: {answer}\n\n"
            "Score (0-10):"
        )

        response = await self._llm.complete(
            [Message(role=MessageRole.USER, content=prompt)],
            temperature=0.0,
            max_tokens=50,
        )

        match = re.search(r"\b(\d+(?:\.\d+)?)\b", response.content)
        raw_score = min(float(match.group(1)), 10.0) if match else 5.0
        score = round(raw_score / 10.0, 4)

        return MetricResult(
            name=self.name,
            score=score,
            reason=response.content.strip(),
        )


class ContextRelevancy(BaseMetric):
    """Measures if the retrieved context is relevant to the query.

    Irrelevant context wastes token budget and can confuse the LLM.
    Good retrieval should return only relevant passages.

    Score interpretation:
        1.0: All context chunks are highly relevant
        0.5: Mixed relevance — some useful, some noise
        0.0: Context is entirely irrelevant to the query
    """

    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "context_relevancy"

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> MetricResult:
        if not contexts:
            return MetricResult(
                name=self.name,
                score=0.0,
                reason="No context provided.",
            )

        relevant_count = 0
        for i, ctx in enumerate(contexts):
            prompt = (
                "Is the following context passage relevant to answering the question?\n"
                "Respond with only 'RELEVANT' or 'NOT RELEVANT'.\n\n"
                f"Question: {query}\n"
                f"Context: {ctx[:500]}\n\n"
                "Verdict:"
            )
            response = await self._llm.complete(
                [Message(role=MessageRole.USER, content=prompt)],
                temperature=0.0,
                max_tokens=20,
            )
            if "NOT RELEVANT" not in response.content.upper() and "RELEVANT" in response.content.upper():
                relevant_count += 1

        score = round(relevant_count / len(contexts), 4) if contexts else 0.0

        return MetricResult(
            name=self.name,
            score=score,
            reason=f"{relevant_count}/{len(contexts)} context chunks relevant.",
            details={"relevant_count": relevant_count, "total_chunks": len(contexts)},
        )
