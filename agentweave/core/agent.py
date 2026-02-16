"""Agent implementation - the core component of AgentWeave.

An Agent is an autonomous unit that can process inputs and generate outputs
using an LLM. Agents can be composed into workflows for complex tasks.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, TYPE_CHECKING

from agentweave.core.config import AgentConfig
from agentweave.core.types import (
    AgentResult,
    LLMResponse,
    Message,
    MessageRole,
    StreamChunk,
    ToolCall,
    Usage,
)
from agentweave.errors.exceptions import AgentExecutionError, ModelNotFoundError
from agentweave.llm.base import BaseLLMProvider
from agentweave.llm.registry import get_registry

if TYPE_CHECKING:
    from agentweave.core.structured import OutputSchema
    from agentweave.memory.base import BaseMemory
    from agentweave.protocols.mcp.client import MCPClient
    from agentweave.tracking.cost import CostTracker
    from agentweave.tracking.callbacks import CallbackManager
    from agentweave.resilience.config import ResilienceConfig
    from agentweave.tools.base import Tool
    from agentweave.tools.executor import ToolExecutor


class Agent:
    """An AI Agent that can process inputs and generate responses.

    Agents are the fundamental building blocks of AgentWeave. Each agent
    has a name, role, and uses an LLM to process inputs.

    Example:
        >>> agent = Agent(
        ...     name="researcher",
        ...     role="정보 검색 전문가",
        ...     model="gpt-4o-mini",
        ... )
        >>> result = agent.run_sync("AI 트렌드에 대해 알려줘")
        >>> print(result.output)

    Attributes:
        name: Unique identifier for the agent.
        role: Description of the agent's role/expertise.
        model: LLM model identifier.
        config: Agent configuration settings.
    """

    def __init__(
        self,
        name: str,
        role: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 60.0,
        system_prompt: str | None = None,
        llm_provider: BaseLLMProvider | None = None,
        # New integration parameters
        memory: "BaseMemory | None" = None,
        cost_tracker: "CostTracker | None" = None,
        resilience: "ResilienceConfig | None" = None,
        tools: "list[Tool] | None" = None,
        callbacks: "CallbackManager | None" = None,
        mcp_client: "MCPClient | None" = None,
    ) -> None:
        """Initialize an Agent.

        Args:
            name: Unique identifier for this agent.
            role: Description of the agent's role or expertise.
            model: LLM model to use (e.g., 'gpt-4o', 'claude-3-5-sonnet', 'ollama/llama3.2').
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            timeout: Timeout in seconds for LLM requests.
            system_prompt: Custom system prompt. If None, uses default.
            llm_provider: Custom LLM provider. If None, auto-detected via registry.
            memory: Memory instance for conversation history.
            cost_tracker: Cost tracker for usage monitoring.
            resilience: Resilience config for retry/circuit breaker.
            tools: List of tools the agent can use.
            callbacks: Callback manager for event notifications.
            mcp_client: MCP client for external tool integration.
        """
        self.name = name
        self.role = role
        self.model = model
        self.config = AgentConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self._system_prompt = system_prompt
        self._provider = llm_provider or get_registry().create_provider(model)

        # Integration components
        self._memory = memory
        self._cost_tracker = cost_tracker
        self._resilience = resilience
        self._callbacks = callbacks
        self._mcp_client = mcp_client

        # Lifecycle
        self._closed = False

        # Tool executor
        self._tool_executor: "ToolExecutor | None" = None
        if tools:
            from agentweave.tools.executor import ToolExecutor
            self._tool_executor = ToolExecutor(tools)

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        if self._system_prompt:
            return self._system_prompt
        return self._default_system_prompt()

    @property
    def memory(self) -> "BaseMemory | None":
        """Get the memory instance."""
        return self._memory

    @property
    def cost_tracker(self) -> "CostTracker | None":
        """Get the cost tracker."""
        return self._cost_tracker

    @property
    def tools(self) -> "list[Tool]":
        """Get registered tools."""
        if self._tool_executor:
            return self._tool_executor.list_tools()
        return []

    @property
    def mcp_client(self) -> "MCPClient | None":
        """Get the MCP client."""
        return self._mcp_client

    async def setup_mcp(self) -> list[str]:
        """Register MCP tools with the agent's tool executor.

        Must be called after MCP client has connected to servers.
        Converts MCP tools to AgentWeave tools and registers them.

        Returns:
            List of registered MCP tool names.
        """
        if not self._mcp_client:
            return []

        from agentweave.protocols.mcp.adapter import register_mcp_tools
        from agentweave.tools.executor import ToolExecutor

        if not self._tool_executor:
            self._tool_executor = ToolExecutor()

        return await register_mcp_tools(self._mcp_client, self._tool_executor)

    def _default_system_prompt(self) -> str:
        """Generate default system prompt based on agent's role."""
        return f"""You are {self.name}, a helpful AI assistant.

Your role: {self.role}

Guidelines:
- Be helpful, accurate, and concise
- Stay focused on your designated role
- Ask for clarification if needed
- Provide actionable responses when possible"""

    def _build_messages(self, input: str) -> list[Message]:
        """Build message list including memory context."""
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
        ]

        # Add memory context if available
        if self._memory is not None:
            recent = self._memory.get_recent(limit=10)
            for entry in recent:
                role = MessageRole.USER if entry.role == "user" else MessageRole.ASSISTANT
                messages.append(Message(role=role, content=entry.content))

        messages.append(Message(role=MessageRole.USER, content=input))
        return messages

    async def _emit_callback(self, event: str, **kwargs: Any) -> None:
        """Emit callback event if callbacks are configured."""
        if self._callbacks:
            from agentweave.tracking.callbacks import CallbackEvent
            try:
                await self._callbacks.emit(
                    CallbackEvent(event),
                    agent_name=self.name,
                    **kwargs,
                )
            except Exception:
                pass  # Don't let callback errors break execution

    async def _execute_llm(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute LLM call with optional resilience."""
        async def _call() -> LLMResponse:
            return await self._provider.complete(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs,
            )

        if self._resilience:
            return await self._resilience.execute(_call, model=self.model)
        return await _call()

    async def run(
        self, input: str, *, max_tool_rounds: int = 10, output_schema: "OutputSchema | None" = None, **kwargs: Any
    ) -> AgentResult:
        """Execute the agent with the given input.

        Args:
            input: User input to process.
            max_tool_rounds: Maximum number of tool calling rounds.
            output_schema: Optional schema for structured JSON output.
            **kwargs: Additional parameters passed to the LLM.

        Returns:
            AgentResult containing the output and metadata.

        Raises:
            AgentExecutionError: If execution fails.
        """
        start_time = time.perf_counter()

        await self._emit_callback("agent_start", input=input)

        messages = self._build_messages(input)

        # Handle structured output
        if output_schema is not None:
            provider_name = self._provider.provider_name
            if provider_name == "openai":
                kwargs["response_format"] = output_schema.to_openai_response_format()
            else:
                # For non-OpenAI providers, inject schema into system prompt
                instruction = output_schema.to_system_prompt_instruction()
                if messages and messages[0].role == MessageRole.SYSTEM:
                    messages[0] = Message(
                        role=MessageRole.SYSTEM,
                        content=messages[0].content + instruction,
                    )

        # Add tools if available
        if self._tool_executor:
            provider_name = self._provider.provider_name
            if provider_name == "openai":
                kwargs["tools"] = self._tool_executor.to_openai_tools()
            elif provider_name == "anthropic":
                kwargs["tools"] = self._tool_executor.to_anthropic_tools()

        # Accumulate usage across tool-calling rounds
        total_prompt_tokens = 0
        total_completion_tokens = 0
        response: LLMResponse | None = None

        try:
            for _round in range(max_tool_rounds):
                await self._emit_callback("llm_start", model=self.model)
                response = await self._execute_llm(messages, **kwargs)
                total_prompt_tokens += response.usage.prompt_tokens
                total_completion_tokens += response.usage.completion_tokens
                await self._emit_callback(
                    "llm_end", model=self.model, tokens=response.usage.total_tokens
                )

                # If no tool calls, we have the final response
                if not response.tool_calls or not self._tool_executor:
                    break

                # Append assistant message with tool calls
                messages.append(Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls,
                ))

                # Execute each tool call
                for tc in response.tool_calls:
                    await self._emit_callback(
                        "tool_start", tool_name=tc.name, arguments=tc.arguments
                    )
                    tool_result = await self._tool_executor.execute(
                        tc.name, tool_call_id=tc.id, **tc.arguments
                    )
                    await self._emit_callback(
                        "tool_end",
                        tool_name=tc.name,
                        result=tool_result.result if tool_result.success else tool_result.error,
                        success=tool_result.success,
                    )

                    # Append tool result message
                    result_content = (
                        str(tool_result.result) if tool_result.success
                        else f"Error: {tool_result.error}"
                    )
                    messages.append(Message(
                        role=MessageRole.TOOL,
                        content=result_content,
                        tool_call_id=tc.id,
                    ))

        except Exception as e:
            await self._emit_callback("agent_error", error=str(e))
            raise AgentExecutionError(
                f"Agent '{self.name}' failed: {e}",
                agent_name=self.name,
            ) from e

        if response is None:
            raise AgentExecutionError(
                f"Agent '{self.name}' produced no response",
                agent_name=self.name,
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Use total accumulated usage
        total_usage = Usage(
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
        )
        cost = self._provider.calculate_cost(
            input_tokens=total_prompt_tokens,
            output_tokens=total_completion_tokens,
        )

        # Track cost if tracker is configured
        if self._cost_tracker:
            from agentweave.tracking.models import TokenUsage
            self._cost_tracker.track_usage(
                model=self.model,
                usage=TokenUsage(
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                ),
                agent_name=self.name,
            )

        # Save to memory if configured
        if self._memory is not None:
            from agentweave.memory.base import MemoryEntry
            self._memory.add(MemoryEntry(content=input, role="user"))
            self._memory.add(MemoryEntry(content=response.content, role="assistant"))

        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response.content,
        )

        # Validate structured output if schema provided
        parsed_output_data: dict[str, Any] | None = None
        if output_schema is not None:
            parsed = output_schema.validate_safe(response.content)
            parsed_output_data = parsed.model_dump() if parsed else None

        result = AgentResult(
            output=response.content,
            parsed_output=parsed_output_data,
            messages=messages + [assistant_message],
            usage=total_usage,
            cost=cost,
            duration_ms=duration_ms,
            metadata={
                "agent_name": self.name,
                "model": self.model,
                "provider": self._provider.provider_name,
                "tool_rounds": _round + 1,
                "output_schema": output_schema.model_class.__name__ if output_schema else None,
            },
        )

        await self._emit_callback(
            "agent_end",
            output=response.content,
            duration_ms=duration_ms,
            cost=cost,
        )

        return result

    async def stream(
        self, input: str, *, max_tool_rounds: int = 10, **kwargs: Any
    ) -> AsyncIterator[StreamChunk]:
        """Stream the agent's response with tool calling support.

        If tools are available and the LLM requests tool calls,
        tools are executed between streaming rounds. Non-streaming
        LLM calls are used for tool-calling rounds, with the final
        text response streamed.

        Args:
            input: User input to process.
            max_tool_rounds: Maximum number of tool calling rounds.
            **kwargs: Additional parameters passed to the LLM.

        Yields:
            StreamChunk with incremental content.
        """
        await self._emit_callback("agent_start", input=input)
        messages = self._build_messages(input)

        # Add tools if available
        if self._tool_executor:
            provider_name = self._provider.provider_name
            if provider_name == "openai":
                kwargs["tools"] = self._tool_executor.to_openai_tools()
            elif provider_name == "anthropic":
                kwargs["tools"] = self._tool_executor.to_anthropic_tools()

        try:
            # Handle tool calling rounds using non-streaming complete()
            for _round in range(max_tool_rounds):
                # First try non-streaming to check for tool calls
                if self._tool_executor:
                    await self._emit_callback("llm_start", model=self.model)
                    response = await self._execute_llm(messages, **kwargs)
                    await self._emit_callback(
                        "llm_end", model=self.model, tokens=response.usage.total_tokens
                    )

                    if response.tool_calls:
                        # Execute tool calls (non-streaming round)
                        messages.append(Message(
                            role=MessageRole.ASSISTANT,
                            content=response.content,
                            tool_calls=response.tool_calls,
                        ))
                        for tc in response.tool_calls:
                            await self._emit_callback(
                                "tool_start", tool_name=tc.name, arguments=tc.arguments
                            )
                            tool_result = await self._tool_executor.execute(
                                tc.name, tool_call_id=tc.id, **tc.arguments
                            )
                            await self._emit_callback(
                                "tool_end",
                                tool_name=tc.name,
                                result=tool_result.result if tool_result.success else tool_result.error,
                                success=tool_result.success,
                            )
                            result_content = (
                                str(tool_result.result) if tool_result.success
                                else f"Error: {tool_result.error}"
                            )
                            messages.append(Message(
                                role=MessageRole.TOOL,
                                content=result_content,
                                tool_call_id=tc.id,
                            ))
                        continue  # Loop back for another round

                    # No tool calls - fall through to stream the final response
                    # But we already have the response from complete(), so yield it as chunks
                    yield StreamChunk(
                        content=response.content,
                        delta=response.content,
                        finish_reason=response.finish_reason,
                        usage=response.usage,
                    )

                    # Track usage
                    if self._cost_tracker:
                        from agentweave.tracking.models import TokenUsage
                        self._cost_tracker.track_usage(
                            model=self.model,
                            usage=TokenUsage(
                                prompt_tokens=response.usage.prompt_tokens,
                                completion_tokens=response.usage.completion_tokens,
                            ),
                            agent_name=self.name,
                        )
                    break
                else:
                    # No tools - pure streaming
                    await self._emit_callback("llm_start", model=self.model)
                    async for chunk in self._provider.stream(
                        messages=messages,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                        **kwargs,
                    ):
                        yield chunk
                        if chunk.usage and self._cost_tracker:
                            from agentweave.tracking.models import TokenUsage
                            self._cost_tracker.track_usage(
                                model=self.model,
                                usage=TokenUsage(
                                    prompt_tokens=chunk.usage.prompt_tokens,
                                    completion_tokens=chunk.usage.completion_tokens,
                                ),
                                agent_name=self.name,
                            )
                    await self._emit_callback("llm_end", model=self.model)
                    break

        except Exception as e:
            await self._emit_callback("agent_error", error=str(e))
            raise AgentExecutionError(
                f"Agent '{self.name}' streaming failed: {e}",
                agent_name=self.name,
            ) from e

        await self._emit_callback("agent_end")

    def run_sync(self, input: str, **kwargs: Any) -> AgentResult:
        """Synchronous version of run().

        Convenience method for non-async contexts.

        Args:
            input: User input to process.
            **kwargs: Additional parameters passed to the LLM.

        Returns:
            AgentResult containing the output and metadata.
        """
        return asyncio.run(self.run(input, **kwargs))

    async def __aenter__(self) -> Agent:
        """Enter async context - load persisted state."""
        self._closed = False
        # Load from memory store if available
        if self._memory is not None and hasattr(self._memory, 'load_from_store'):
            await self._memory.load_from_store()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context - flush state and cleanup resources."""
        if self._closed:
            return
        self._closed = True

        # Flush memory to store if available
        if self._memory is not None and hasattr(self._memory, 'save_to_store'):
            try:
                await self._memory.save_to_store()
            except Exception:
                pass  # Don't mask the original exception

        # Disconnect MCP client if we own it
        if self._mcp_client is not None and hasattr(self._mcp_client, 'disconnect_all'):
            try:
                await self._mcp_client.disconnect_all()
            except Exception:
                pass  # Don't mask the original exception

    async def close(self) -> None:
        """Explicitly cleanup agent resources.

        Flushes memory to persistent store and disconnects external services.
        Called automatically when using agent as async context manager.
        Safe to call multiple times (idempotent).
        """
        await self.__aexit__(None, None, None)

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, role={self.role!r}, model={self.model!r})"
