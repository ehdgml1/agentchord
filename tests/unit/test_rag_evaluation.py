"""Tests for RAG evaluation metrics."""
import pytest
from agentchord.rag.evaluation.metrics import (
    AnswerRelevancy,
    ContextRelevancy,
    Faithfulness,
    MetricResult,
)
from agentchord.rag.evaluation.evaluator import EvaluationResult, RAGEvaluator
from agentchord.rag.types import RAGResponse, RetrievalResult
from tests.conftest import MockLLMProvider


class TestMetricResult:
    def test_create(self):
        result = MetricResult(name="test", score=0.9)
        assert result.name == "test"
        assert result.score == 0.9
        assert result.reason == ""
        assert result.details == {}

    def test_with_reason_and_details(self):
        result = MetricResult(
            name="faith",
            score=0.75,
            reason="3/4 claims supported",
            details={"supported": 3, "total": 4},
        )
        assert result.reason == "3/4 claims supported"
        assert result.details["supported"] == 3


class TestEvaluationResult:
    def test_ragas_score_harmonic_mean(self):
        metrics = [
            MetricResult(name="a", score=0.8),
            MetricResult(name="b", score=0.6),
            MetricResult(name="c", score=1.0),
        ]
        result = EvaluationResult(metrics=metrics)
        score = result.ragas_score
        assert 0 < score < 1
        # Harmonic mean should be less than or equal to arithmetic mean
        assert score <= (0.8 + 0.6 + 1.0) / 3

    def test_ragas_score_empty(self):
        result = EvaluationResult()
        assert result.ragas_score == 0.0

    def test_ragas_score_with_zero(self):
        metrics = [
            MetricResult(name="a", score=0.0),
            MetricResult(name="b", score=0.8),
        ]
        result = EvaluationResult(metrics=metrics)
        # Zero scores should be excluded from harmonic mean
        assert result.ragas_score == 0.8

    def test_ragas_score_all_zeros(self):
        metrics = [
            MetricResult(name="a", score=0.0),
            MetricResult(name="b", score=0.0),
        ]
        result = EvaluationResult(metrics=metrics)
        assert result.ragas_score == 0.0

    def test_get_metric(self):
        metrics = [MetricResult(name="faith", score=0.9)]
        result = EvaluationResult(metrics=metrics)
        assert result.get_metric("faith") is not None
        assert result.get_metric("faith").score == 0.9
        assert result.get_metric("nonexistent") is None

    def test_summary(self):
        metrics = [
            MetricResult(name="a", score=0.8),
            MetricResult(name="b", score=0.6),
        ]
        result = EvaluationResult(metrics=metrics)
        summary = result.summary()
        assert "a" in summary
        assert "b" in summary
        assert "ragas_score" in summary
        assert summary["a"] == 0.8
        assert summary["b"] == 0.6

    def test_ragas_score_single_metric(self):
        metrics = [MetricResult(name="a", score=0.7)]
        result = EvaluationResult(metrics=metrics)
        assert result.ragas_score == pytest.approx(0.7)


class TestFaithfulness:
    async def test_evaluate(self):
        provider = MockLLMProvider(response_content="- Claim one\n- Claim two")
        metric = Faithfulness(provider)
        result = await metric.evaluate(
            query="What?",
            answer="Answer with claims",
            contexts=["Context text"],
        )
        assert result.name == "faithfulness"
        assert 0 <= result.score <= 1

    async def test_no_claims(self):
        provider = MockLLMProvider(response_content="No bullet points here")
        metric = Faithfulness(provider)
        result = await metric.evaluate(
            query="q", answer="a", contexts=["c"],
        )
        # No claims parsed -> score 1.0
        assert result.score == 1.0

    async def test_faithfulness_name(self):
        provider = MockLLMProvider()
        metric = Faithfulness(provider)
        assert metric.name == "faithfulness"


class TestAnswerRelevancy:
    async def test_evaluate(self):
        provider = MockLLMProvider(response_content="8")
        metric = AnswerRelevancy(provider)
        result = await metric.evaluate(
            query="What is Python?",
            answer="Python is a programming language.",
            contexts=["context"],
        )
        assert result.name == "answer_relevancy"
        assert result.score == 0.8

    async def test_no_score_found(self):
        provider = MockLLMProvider(response_content="no number here")
        metric = AnswerRelevancy(provider)
        result = await metric.evaluate("q", "a", ["c"])
        assert result.score == 0.5  # default

    async def test_score_clamped_to_one(self):
        provider = MockLLMProvider(response_content="15")
        metric = AnswerRelevancy(provider)
        result = await metric.evaluate("q", "a", ["c"])
        assert result.score == 1.0  # clamped at 10/10

    async def test_answer_relevancy_name(self):
        provider = MockLLMProvider()
        metric = AnswerRelevancy(provider)
        assert metric.name == "answer_relevancy"


class TestContextRelevancy:
    async def test_evaluate(self):
        provider = MockLLMProvider(response_content="RELEVANT")
        metric = ContextRelevancy(provider)
        result = await metric.evaluate(
            query="What is AI?",
            answer="answer",
            contexts=["AI is artificial intelligence"],
        )
        assert result.name == "context_relevancy"
        assert result.score == 1.0

    async def test_empty_contexts(self):
        provider = MockLLMProvider(response_content="RELEVANT")
        metric = ContextRelevancy(provider)
        result = await metric.evaluate("q", "a", [])
        assert result.score == 0.0

    async def test_context_relevancy_name(self):
        provider = MockLLMProvider()
        metric = ContextRelevancy(provider)
        assert metric.name == "context_relevancy"

    async def test_multiple_contexts(self):
        provider = MockLLMProvider(response_content="RELEVANT")
        metric = ContextRelevancy(provider)
        result = await metric.evaluate(
            query="q",
            answer="a",
            contexts=["context1", "context2", "context3"],
        )
        # MockLLMProvider always returns "RELEVANT" so all 3 pass
        assert result.score == 1.0


class TestRAGEvaluator:
    async def test_evaluate(self):
        provider = MockLLMProvider(response_content="8")
        evaluator = RAGEvaluator(llm=provider)
        result = await evaluator.evaluate(
            query="What?",
            answer="Answer",
            contexts=["Context"],
        )
        assert len(result.metrics) == 3
        assert result.ragas_score > 0

    async def test_evaluate_response(self):
        provider = MockLLMProvider(response_content="8")
        evaluator = RAGEvaluator(llm=provider)
        rag_response = RAGResponse(
            query="q",
            answer="a",
            retrieval=RetrievalResult(query="q"),
        )
        result = await evaluator.evaluate_response(rag_response)
        assert len(result.metrics) == 3

    async def test_custom_metrics(self):
        provider = MockLLMProvider(response_content="8")
        evaluator = RAGEvaluator(
            llm=provider,
            metrics=[AnswerRelevancy(provider)],
        )
        result = await evaluator.evaluate("q", "a", ["c"])
        assert len(result.metrics) == 1

    async def test_add_metric(self):
        provider = MockLLMProvider(response_content="8")
        evaluator = RAGEvaluator(llm=provider, metrics=[])
        evaluator.add_metric(AnswerRelevancy(provider))
        result = await evaluator.evaluate("q", "a", ["c"])
        assert len(result.metrics) == 1

    async def test_default_metrics_are_three(self):
        provider = MockLLMProvider()
        evaluator = RAGEvaluator(llm=provider)
        # Default: Faithfulness, AnswerRelevancy, ContextRelevancy
        result = await evaluator.evaluate("q", "a", ["c"])
        metric_names = {m.name for m in result.metrics}
        assert "faithfulness" in metric_names
        assert "answer_relevancy" in metric_names
        assert "context_relevancy" in metric_names
