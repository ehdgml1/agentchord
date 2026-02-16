"""RAG evaluation orchestrator.

Runs multiple evaluation metrics and computes aggregate scores
including the RAGAS composite score (harmonic mean).

Example:
    evaluator = RAGEvaluator(llm=provider)
    result = await evaluator.evaluate(
        query="What is AgentWeave?",
        answer="AgentWeave is a multi-agent framework.",
        contexts=["AgentWeave is a protocol-first multi-agent framework."],
    )
    print(f"RAGAS Score: {result.ragas_score:.2f}")
    for m in result.metrics:
        print(f"  {m.name}: {m.score:.2f}")
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from agentweave.llm.base import BaseLLMProvider
from agentweave.rag.evaluation.metrics import (
    AnswerRelevancy,
    BaseMetric,
    ContextRelevancy,
    Faithfulness,
    MetricResult,
)
from agentweave.rag.types import RAGResponse


@dataclass
class EvaluationResult:
    """Complete evaluation result with all metric scores."""

    metrics: list[MetricResult] = field(default_factory=list)

    @property
    def ragas_score(self) -> float:
        """Compute RAGAS score as harmonic mean of all metrics.

        Harmonic mean penalizes low scores more than arithmetic mean,
        ensuring all metrics must be good for a high overall score.

        Returns:
            RAGAS score between 0 and 1.
        """
        scores = [m.score for m in self.metrics if m.score > 0]
        if not scores:
            return 0.0
        n = len(scores)
        harmonic_sum = sum(1.0 / s for s in scores)
        return round(n / harmonic_sum, 4)

    def get_metric(self, name: str) -> MetricResult | None:
        """Get a specific metric result by name."""
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def summary(self) -> dict[str, float]:
        """Get summary dict of all metric scores."""
        result: dict[str, float] = {}
        for m in self.metrics:
            result[m.name] = m.score
        result["ragas_score"] = self.ragas_score
        return result


class RAGEvaluator:
    """Evaluator for RAG pipeline quality.

    Runs Faithfulness, Answer Relevancy, and Context Relevancy
    metrics and computes the RAGAS composite score.

    Custom metrics can be added via add_metric().
    """

    def __init__(
        self,
        llm: BaseLLMProvider,
        *,
        metrics: list[BaseMetric] | None = None,
    ) -> None:
        """Initialize evaluator.

        Args:
            llm: LLM provider for metric evaluation.
            metrics: Custom metrics. Defaults to standard RAGAS metrics.
        """
        self._llm = llm
        if metrics is not None:
            self._metrics = list(metrics)
        else:
            self._metrics: list[BaseMetric] = [
                Faithfulness(llm),
                AnswerRelevancy(llm),
                ContextRelevancy(llm),
            ]

    def add_metric(self, metric: BaseMetric) -> None:
        """Add a custom evaluation metric."""
        self._metrics.append(metric)

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> EvaluationResult:
        """Run all metrics and return evaluation result.

        Args:
            query: Original user question.
            answer: Generated answer.
            contexts: Retrieved context strings.

        Returns:
            EvaluationResult with all metric scores and RAGAS score.
        """
        results = list(await asyncio.gather(
            *[metric.evaluate(query, answer, contexts) for metric in self._metrics]
        ))
        return EvaluationResult(metrics=results)

    async def evaluate_response(self, response: RAGResponse) -> EvaluationResult:
        """Evaluate a RAGResponse directly.

        Convenience method that extracts query, answer, and contexts
        from a RAGResponse object.

        Args:
            response: RAGResponse from pipeline.query().

        Returns:
            EvaluationResult with all metric scores.
        """
        return await self.evaluate(
            query=response.query,
            answer=response.answer,
            contexts=response.retrieval.contexts,
        )
