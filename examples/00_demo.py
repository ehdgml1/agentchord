#!/usr/bin/env python3
"""AgentWeave Demo - API Key Free Examples

이 스크립트는 실제 API 키 없이 AgentWeave의 주요 기능을 시연합니다.
Mock LLM Provider를 사용하여 완전히 독립적으로 실행됩니다.

실행 방법:
    python examples/00_demo.py

3가지 데모 시나리오:
    1. Tool Calling Agent - 도구를 호출하는 에이전트
    2. Multi-Agent Workflow - 3개 에이전트 파이프라인
    3. RAG Pipeline - 문서 검색 및 답변 생성

필요 패키지:
    pip install agentweave[rag]  # rich는 기본 의존성에 포함
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, AsyncIterator

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Core imports
from agentweave.core.agent import Agent
from agentweave.core.workflow import Workflow
from agentweave.core.types import (
    LLMResponse,
    Message,
    MessageRole,
    StreamChunk,
    ToolCall,
    Usage,
)
from agentweave.llm.base import BaseLLMProvider
from agentweave.tracking.cost import CostTracker
from agentweave.tracking.models import TokenUsage

# Tool imports
from agentweave.tools.decorator import tool

# RAG imports
from agentweave.rag.pipeline import RAGPipeline
from agentweave.rag.types import Document
from agentweave.rag.embeddings.base import EmbeddingProvider
from agentweave.rag.vectorstore.in_memory import InMemoryVectorStore


console = Console()


# ============================================================================
# Mock Provider Implementation (No API Key Required)
# ============================================================================


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider that generates deterministic embeddings."""

    @property
    def model_name(self) -> str:
        return "mock-embeddings-v1"

    @property
    def dimensions(self) -> int:
        return 384

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding based on text hash."""
        # Simple hash-based embedding for demo purposes
        text_hash = hash(text) % (2**32)
        random.seed(text_hash)
        return [random.gauss(0, 1) for _ in range(self.dimensions)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed multiple texts."""
        return [await self.embed(text) for text in texts]


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for demo purposes.

    Simulates tool calling and natural language responses without API calls.
    """

    def __init__(self, model: str = "mock-gpt-4o-mini"):
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.00015  # Mock pricing similar to gpt-4o-mini

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0006

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate mock completion with tool calling support."""
        # Simulate processing time
        await asyncio.sleep(0.1)

        last_message = messages[-1].content if messages else ""

        # Check if tools are available and should be called
        tools = kwargs.get("tools", [])
        response_format = kwargs.get("response_format")

        # Simulate tool calling logic
        if tools and any(keyword in last_message.lower() for keyword in ["계산", "더하기", "곱하기", "add", "multiply"]):
            tool_calls = self._generate_tool_calls(last_message, tools)
            if tool_calls:
                return LLMResponse(
                    content="도구를 사용하여 계산하겠습니다.",
                    model=self._model,
                    usage=Usage(prompt_tokens=50, completion_tokens=20),
                    finish_reason="tool_calls",
                    tool_calls=tool_calls,
                )

        # Generate contextual response based on agent role
        content = self._generate_response(messages, response_format)

        # Simulate token usage
        prompt_tokens = sum(len(m.content.split()) * 1.3 for m in messages)
        completion_tokens = len(content.split()) * 1.3

        return LLMResponse(
            content=content,
            model=self._model,
            usage=Usage(
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
            ),
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream mock response chunk by chunk."""
        response = await self.complete(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

        # Split response into chunks
        words = response.content.split()
        accumulated = ""

        for i, word in enumerate(words):
            accumulated += word + " "
            await asyncio.sleep(0.05)  # Simulate streaming delay

            is_last = i == len(words) - 1
            yield StreamChunk(
                content=accumulated.strip(),
                delta=word + " ",
                finish_reason="stop" if is_last else None,
                usage=response.usage if is_last else None,
            )

    def _generate_tool_calls(self, message: str, tools: list[dict]) -> list[ToolCall]:
        """Generate appropriate tool calls based on message content."""
        tool_calls = []

        # Simple pattern matching for demo
        if "더하기" in message or "add" in message.lower():
            if any(t.get("function", {}).get("name") == "add" for t in tools):
                tool_calls.append(ToolCall(
                    id="call_1",
                    name="add",
                    arguments={"a": 5, "b": 3},
                ))

        if "곱하기" in message or "multiply" in message.lower():
            if any(t.get("function", {}).get("name") == "multiply" for t in tools):
                tool_calls.append(ToolCall(
                    id="call_2",
                    name="multiply",
                    arguments={"a": 4, "b": 7},
                ))

        return tool_calls

    def _generate_response(self, messages: list[Message], response_format: Any = None) -> str:
        """Generate contextual response based on conversation history."""
        # Extract role from system message
        system_msg = next((m for m in messages if m.role == MessageRole.SYSTEM), None)
        role = "assistant"

        if system_msg:
            content = system_msg.content.lower()
            if "researcher" in content or "연구" in content:
                role = "researcher"
            elif "writer" in content or "작가" in content:
                role = "writer"
            elif "reviewer" in content or "검토" in content:
                role = "reviewer"
            elif "calculator" in content or "계산" in content:
                role = "calculator"

        last_user_msg = next((m.content for m in reversed(messages) if m.role == MessageRole.USER), "")

        # Role-specific responses
        if role == "researcher":
            return (
                "연구 결과를 종합하면, AgentWeave는 강력한 AI 에이전트 프레임워크입니다. "
                "멀티 에이전트 협업, RAG, 도구 호출 등 다양한 기능을 제공합니다. "
                "Python 3.10+ 환경에서 작동하며, OpenAI, Anthropic, Ollama 등 여러 LLM을 지원합니다."
            )
        elif role == "writer":
            return (
                "# AgentWeave 소개\n\n"
                "AgentWeave는 현대적인 AI 에이전트 개발을 위한 종합 프레임워크입니다. "
                "연구 자료에 따르면, 이 프레임워크는 다음과 같은 특징을 가지고 있습니다:\n\n"
                "- **멀티 에이전트 시스템**: 여러 에이전트를 조율하여 복잡한 작업 수행\n"
                "- **RAG 지원**: 벡터 검색과 하이브리드 검색으로 정확한 정보 제공\n"
                "- **도구 통합**: Function calling을 통한 외부 도구 활용\n\n"
                "개발자 친화적인 API와 풍부한 문서를 제공합니다."
            )
        elif role == "reviewer":
            return (
                "검토 의견:\n\n"
                "✅ 구조가 명확하고 이해하기 쉽습니다\n"
                "✅ 주요 기능이 잘 설명되어 있습니다\n"
                "⚠️  코드 예제를 추가하면 더 좋을 것 같습니다\n"
                "⚠️  성능 벤치마크 정보가 있으면 유용할 것 같습니다\n\n"
                "전반적으로 우수한 내용이며, 약간의 보완만 있으면 완벽합니다."
            )
        elif role == "calculator":
            return "도구를 사용한 계산 결과를 확인해주세요."

        # Structured output handling
        if response_format:
            return '{"summary": "Mock structured output", "confidence": 0.95}'

        # Default response
        return f"이해했습니다. '{last_user_msg[:50]}...'에 대해 처리하겠습니다."


# ============================================================================
# Demo 1: Tool Calling Agent
# ============================================================================


@tool(description="두 숫자를 더합니다")
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@tool(description="두 숫자를 곱합니다")
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together."""
    return a * b


async def demo_tool_calling():
    """Demo 1: Tool calling agent with calculator tools."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Demo 1: Tool Calling Agent[/bold cyan]\n"
        "Calculator agent using @tool decorator",
        border_style="cyan"
    ))

    # Create cost tracker
    cost_tracker = CostTracker(budget_limit=1.0)

    # Create agent with tools
    agent = Agent(
        name="calculator",
        role="수학 계산을 도와주는 AI 계산기",
        model="mock-gpt-4o-mini",
        llm_provider=MockLLMProvider(),
        tools=[add, multiply],
        cost_tracker=cost_tracker,
    )

    console.print("\n[yellow]Input:[/yellow] 5 더하기 3을 계산하고, 그 결과에 4를 곱해줘")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=None)
        result = await agent.run("5 더하기 3을 계산하고, 그 결과에 4를 곱해줘", max_tool_rounds=5)
        progress.remove_task(task)

    console.print(f"\n[green]Output:[/green] {result.output}")
    console.print(f"\n[dim]Tokens: {result.usage.total_tokens} | Cost: ${result.cost:.6f} | Duration: {result.duration_ms}ms[/dim]")

    # Show cost summary
    summary = cost_tracker.get_summary()
    console.print(f"\n[bold]Total Cost:[/bold] ${summary.total_cost_usd:.6f}")
    console.print(f"[bold]Total Tokens:[/bold] {summary.total_tokens}")


# ============================================================================
# Demo 2: Multi-Agent Workflow
# ============================================================================


async def demo_multi_agent_workflow():
    """Demo 2: Multi-agent pipeline with 3 specialized agents."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold magenta]Demo 2: Multi-Agent Workflow[/bold magenta]\n"
        "Pipeline: Researcher → Writer → Reviewer",
        border_style="magenta"
    ))

    # Create cost tracker for the entire workflow
    cost_tracker = CostTracker(budget_limit=5.0)

    # Create specialized agents
    researcher = Agent(
        name="researcher",
        role="AI 및 기술 트렌드 연구 전문가",
        model="mock-gpt-4o-mini",
        llm_provider=MockLLMProvider("mock-gpt-4o-mini"),
        cost_tracker=cost_tracker,
    )

    writer = Agent(
        name="writer",
        role="기술 문서 작성 전문가",
        model="mock-gpt-4o-mini",
        llm_provider=MockLLMProvider("mock-gpt-4o-mini"),
        cost_tracker=cost_tracker,
    )

    reviewer = Agent(
        name="reviewer",
        role="콘텐츠 품질 검토 전문가",
        model="mock-gpt-4o-mini",
        llm_provider=MockLLMProvider("mock-gpt-4o-mini"),
        cost_tracker=cost_tracker,
    )

    # Create workflow
    workflow = Workflow(
        agents=[researcher, writer, reviewer],
        flow="researcher -> writer -> reviewer",
    )

    console.print("\n[yellow]Input:[/yellow] AgentWeave 프레임워크에 대한 소개 글을 작성해주세요")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing workflow...", total=None)
        result = await workflow.run("AgentWeave 프레임워크에 대한 소개 글을 작성해주세요")
        progress.remove_task(task)

    console.print(f"\n[green]Final Output:[/green]\n{result.output}")

    # Show execution details
    table = Table(title="Workflow Execution Details")
    table.add_column("Agent", style="cyan")
    table.add_column("Output Preview", style="white")

    for agent_result in result.state.history:
        agent_name = agent_result.metadata.get("agent_name", "unknown")
        output = agent_result.output
        preview = output[:100] + "..." if len(output) > 100 else output
        table.add_row(agent_name, preview)

    console.print("\n")
    console.print(table)

    # Show cost breakdown
    summary = cost_tracker.get_summary()
    console.print(f"\n[bold]Total Cost:[/bold] ${summary.total_cost_usd:.6f}")
    console.print(f"[bold]Total Tokens:[/bold] {summary.total_tokens}")


# ============================================================================
# Demo 3: RAG Pipeline
# ============================================================================


async def demo_rag_pipeline():
    """Demo 3: RAG pipeline with document ingestion and retrieval."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]Demo 3: RAG Pipeline[/bold green]\n"
        "Ingest → Retrieve → Generate",
        border_style="green"
    ))

    # Create providers
    llm = MockLLMProvider("mock-gpt-4o-mini")
    embeddings = MockEmbeddingProvider()
    vectorstore = InMemoryVectorStore()

    # Create RAG pipeline
    pipeline = RAGPipeline(
        llm=llm,
        embedding_provider=embeddings,
        vectorstore=vectorstore,
        search_limit=3,
    )

    # Create sample documents
    documents = [
        Document(
            content=(
                "AgentWeave는 Python으로 작성된 강력한 AI 에이전트 프레임워크입니다. "
                "멀티 에이전트 시스템, RAG, 도구 호출 등을 지원합니다. "
                "OpenAI, Anthropic, Ollama 등 여러 LLM 프로바이더를 사용할 수 있습니다."
            ),
            source="docs/intro.txt",
            metadata={"section": "introduction"},
        ),
        Document(
            content=(
                "AgentWeave의 주요 기능:\n"
                "1. Agent - 단일 AI 에이전트로 작업 수행\n"
                "2. Workflow - 여러 에이전트를 조율하여 복잡한 작업 수행\n"
                "3. RAG Pipeline - 문서 검색 및 답변 생성\n"
                "4. Tool Calling - @tool 데코레이터로 함수를 도구로 등록\n"
                "5. Memory - 대화 히스토리 관리 및 영속성 지원"
            ),
            source="docs/features.txt",
            metadata={"section": "features"},
        ),
        Document(
            content=(
                "AgentWeave 설치 방법:\n"
                "pip install agentweave\n\n"
                "RAG 기능을 사용하려면:\n"
                "pip install agentweave[rag]\n\n"
                "모든 선택적 의존성 포함:\n"
                "pip install agentweave[all]"
            ),
            source="docs/installation.txt",
            metadata={"section": "installation"},
        ),
    ]

    # Ingest documents
    console.print("\n[yellow]Ingesting documents...[/yellow]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Chunking and embedding...", total=None)
        count = await pipeline.ingest_documents(documents)
        progress.remove_task(task)

    console.print(f"[green]✓[/green] Ingested {count} chunks")

    # Query the pipeline
    queries = [
        "AgentWeave가 무엇인가요?",
        "어떤 기능들을 제공하나요?",
        "어떻게 설치하나요?",
    ]

    for query in queries:
        console.print(f"\n[yellow]Query:[/yellow] {query}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Searching and generating...", total=None)
            response = await pipeline.query(query, limit=2)
            progress.remove_task(task)

        console.print(f"[green]Answer:[/green] {response.answer}")
        console.print(f"[dim]Retrieved {len(response.retrieval.results)} chunks in {response.retrieval.total_ms:.1f}ms[/dim]")

    await pipeline.close()


# ============================================================================
# Main Entry Point
# ============================================================================


async def main():
    """Run all demo scenarios."""
    console.print(Panel.fit(
        "[bold white]AgentWeave Demo Suite[/bold white]\n"
        "[dim]No API keys required - fully self-contained demonstrations[/dim]",
        border_style="bright_white"
    ))

    try:
        # Run all demos
        await demo_tool_calling()
        await demo_multi_agent_workflow()
        await demo_rag_pipeline()

        # Summary
        console.print("\n")
        console.print(Panel.fit(
            "[bold green]✓ All demos completed successfully![/bold green]\n\n"
            "Next steps:\n"
            "• Replace MockLLMProvider with real providers (OpenAI, Anthropic, etc.)\n"
            "• Explore advanced features in other examples/\n"
            "• Read the documentation at https://agentweave.dev",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
