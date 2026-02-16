# Streaming Guide

AgentWeave supports streaming responses from all LLM providers, enabling real-time token-by-token delivery for interactive applications.

## Quick Start

Stream responses token by token:

```python
from agentweave import Agent

agent = Agent(
    name="assistant",
    role="Helpful AI",
    model="gpt-4o-mini"
)

# Stream response
async for chunk in agent.stream("Tell me a short story"):
    print(chunk.delta, end="", flush=True)
print()  # Newline after stream
```

Output:
```
Once upon a time, there was a small village... [continues streaming]
```

## StreamChunk

Each streamed response yields a `StreamChunk` object:

```python
from agentweave.core.types import StreamChunk

# Each chunk contains:
chunk = StreamChunk(
    content="Complete content so far",      # Full accumulated text
    delta="Next chunk",                      # Just the new text
    finish_reason=None,                      # None until end
    usage=None                               # Usage stats (last chunk only)
)

print(chunk.content)       # "Complete content so farNext chunk"
print(chunk.delta)         # "Next chunk"
print(chunk.finish_reason) # None (not done yet)
print(chunk.usage)         # None (not last chunk)
```

### Properties

| Property | Type | Meaning |
|----------|------|---------|
| `content` | str | Full accumulated response so far |
| `delta` | str | New text in this chunk (the "delta") |
| `finish_reason` | str or None | `"stop"` on last chunk, else `None` |
| `usage` | Usage or None | Token counts on last chunk only |

## Basic Streaming

Stream without tools:

```python
agent = Agent(
    name="storyteller",
    role="Creative writer",
    model="gpt-4o-mini"
)

# Stream and print in real-time
async for chunk in agent.stream("Write a limerick about cats"):
    print(chunk.delta, end="", flush=True)

print()  # Final newline
```

## Streaming with Tools

Agents with tools use a hybrid approach:

1. **Tool Calling Phase**: Agent calls tools (no streaming)
2. **Response Phase**: Final response is streamed

```python
from agentweave import Agent, tool

@tool(description="Get current temperature in Celsius")
def get_temperature() -> float:
    return 22.5

@tool(description="Convert Celsius to Fahrenheit")
def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9/5) + 32

agent = Agent(
    name="weather",
    role="Weather assistant",
    model="gpt-4o-mini",
    tools=[get_temperature, celsius_to_fahrenheit]
)

# Agent will:
# 1. Call get_temperature() -> 22.5
# 2. Call celsius_to_fahrenheit(22.5) -> 72.5
# 3. Stream the response about current temperature
async for chunk in agent.stream("What's the temperature in Fahrenheit?"):
    print(chunk.delta, end="", flush=True)
```

Process:
```
User query
    ↓
Agent runs tools (not streamed):
    - get_temperature() → 22.5
    - celsius_to_fahrenheit(22.5) → 72.5
    ↓
Agent generates response (streamed):
    - "The current temperature is 72.5 F..." [token 1]
    - " degrees, which is quite comfortable." [token 2]
    ↓
User sees real-time stream
```

### Tool Calling Details

```python
# With tools present
async for chunk in agent.stream("Calculate 10 + 5"):
    # Chunk 1: "" (tool calling phase, no content yet)
    # Chunk 2: "The result of 10 + 5 is 15." (streaming starts)
    # Chunk 3: More of the response...
    # Last chunk: finish_reason="stop", usage=Usage(...)
    print(chunk.delta, end="", flush=True)
```

The tool phase happens silently - you only see chunks once tool results are ready.

## Streaming Architecture

### Without Tools

Pure streaming mode:

```
LLM Provider
    ↓ stream tokens
StreamChunk 1: content="Once upon"
StreamChunk 2: content="Once upon a"
StreamChunk 3: content="Once upon a time"
...
StreamChunk N: content="...", finish_reason="stop", usage=Usage(...)
```

### With Tools

Hybrid mode (complete for tools, stream for final):

```
LLM Provider
    ↓ complete() to get tool calls
Tool Results Available
    ↓ stream() for final response
StreamChunk 1: content="Based on..."
StreamChunk 2: content="Based on the search..."
...
StreamChunk N: content="...", finish_reason="stop"
```

## Usage Statistics

Token usage is only available on the final chunk:

```python
async for chunk in agent.stream("Tell me something"):
    if chunk.finish_reason == "stop":
        # Last chunk - has usage info
        print(f"Tokens: {chunk.usage.total_tokens}")
        print(f"Cost: ${chunk.usage.completion_tokens * 0.00015 / 1000:.4f}")
    else:
        # Not the last chunk - no usage yet
        assert chunk.usage is None
```

Get final result after streaming:

```python
async for chunk in agent.stream("Query"):
    pass  # Continue until stream ends

# After loop exits:
if chunk.finish_reason == "stop":
    print(f"Final token count: {chunk.usage.total_tokens}")
```

## Building Responses

### Accumulate Full Response

```python
response_parts = []

async for chunk in agent.stream("Hello"):
    response_parts.append(chunk.delta)

full_response = "".join(response_parts)
print(f"Full response: {full_response}")
```

Or use the `content` field (already accumulated):

```python
last_chunk = None

async for chunk in agent.stream("Hello"):
    last_chunk = chunk

full_response = last_chunk.content if last_chunk else ""
```

### Display in Real-Time

```python
async for chunk in agent.stream("Write a poem"):
    # Print immediately as tokens arrive
    print(chunk.delta, end="", flush=True)

print()  # Final newline
```

### Hybrid: Buffer and Display

```python
buffer = ""
buffer_size = 5  # Buffer until we have 5 chars

async for chunk in agent.stream("Tell a story"):
    buffer += chunk.delta

    if len(buffer) >= buffer_size or chunk.finish_reason:
        print(buffer, end="", flush=True)
        buffer = ""
```

## Error Handling

Streaming can raise exceptions:

```python
try:
    async for chunk in agent.stream("Query"):
        print(chunk.delta, end="", flush=True)
except asyncio.TimeoutError:
    print("\nStream timed out")
except Exception as e:
    print(f"\nStream error: {e}")
```

The stream can fail at any point:

```python
content = ""

try:
    async for chunk in agent.stream("Query"):
        content += chunk.delta
        print(chunk.delta, end="", flush=True)
except Exception as e:
    # Partial content is available
    print(f"\nError after: {len(content)} characters")
    print(f"Partial result: {content}")
```

## Advanced Usage

### Custom Streaming Handler

```python
async def stream_with_handler(agent, prompt, handler):
    """Stream with custom processing."""
    async for chunk in agent.stream(prompt):
        # Custom handler for each chunk
        await handler(chunk)

async def my_handler(chunk):
    """Example handler."""
    if chunk.delta:
        print(f"[CHUNK] {chunk.delta}")
    if chunk.finish_reason:
        print(f"[DONE] usage={chunk.usage}")

# Usage
await stream_with_handler(agent, "Tell me a story", my_handler)
```

### Rate Limiting

Slow down streaming for display:

```python
import asyncio

async for chunk in agent.stream("Long response"):
    print(chunk.delta, end="", flush=True)
    await asyncio.sleep(0.01)  # 10ms per chunk
```

### Streaming to File

```python
with open("response.txt", "w") as f:
    async for chunk in agent.stream("Write an essay"):
        f.write(chunk.delta)
        f.flush()  # Flush after each chunk
```

### Streaming with Progress

```python
total_chars = 0

async for chunk in agent.stream("Long response"):
    total_chars += len(chunk.delta)
    print(chunk.delta, end="", flush=True)

    # Show progress
    if total_chars % 100 == 0:
        print(f" [{total_chars}]", end="\r", flush=True)
```

### Streaming to WebSocket

```python
async def stream_to_websocket(agent, prompt, websocket):
    """Stream response to WebSocket client."""
    async for chunk in agent.stream(prompt):
        # Send each chunk to client
        await websocket.send_json({
            "type": "chunk",
            "delta": chunk.delta,
            "finish_reason": chunk.finish_reason,
            "usage": chunk.usage.model_dump() if chunk.usage else None
        })
```

### Collecting All Chunks

```python
chunks = []

async for chunk in agent.stream("Query"):
    chunks.append(chunk)

# Analyze stream
print(f"Total chunks: {len(chunks)}")
print(f"Total tokens: {chunks[-1].usage.total_tokens}")
print(f"Avg chunk size: {sum(len(c.delta) for c in chunks) / len(chunks):.1f} chars")
```

## Provider-Specific Notes

### OpenAI

Full streaming support. Works with all models.

```python
agent = Agent(model="gpt-4o-mini")

async for chunk in agent.stream("Hello"):
    print(chunk.delta, end="", flush=True)
```

### Anthropic

Full streaming support. Works with Claude models.

```python
agent = Agent(model="claude-3-5-sonnet")

async for chunk in agent.stream("Hello"):
    print(chunk.delta, end="", flush=True)
```

### Gemini

Full streaming support. Works with Gemini models.

```python
agent = Agent(model="gemini-2.0-flash")

async for chunk in agent.stream("Hello"):
    print(chunk.delta, end="", flush=True)
```

### Ollama

Full streaming support. Works with local models.

```python
agent = Agent(model="ollama/llama3.2")

async for chunk in agent.stream("Hello"):
    print(chunk.delta, end="", flush=True)
```

## Performance Considerations

### Token Efficiency

Streaming is equally token-efficient - you pay per token regardless:

```python
# Same cost regardless of streaming or not
result1 = agent.run_sync("Write a poem")  # 150 tokens
result2 = await agent.stream("Write a poem")  # 150 tokens (accumulated)
```

### Memory Usage

Streaming uses less memory per chunk:

```python
# Without streaming: entire response in memory
result = agent.run_sync("Long response")  # Entire response in memory

# With streaming: one chunk at a time
async for chunk in agent.stream("Long response"):  # ~100-200 chars per chunk
    print(chunk.delta)
```

### Latency

Streaming gives better user experience - show content as it arrives:

```python
# Without streaming: Wait for entire response
start = time.time()
result = agent.run_sync("Query")
elapsed = time.time() - start
# User sees nothing for `elapsed` seconds, then full response

# With streaming: Show content immediately
start = time.time()
first_chunk = True
async for chunk in agent.stream("Query"):
    if first_chunk:
        print(f"First token in {time.time() - start:.2f}s")
        first_chunk = False
    print(chunk.delta, end="", flush=True)
# User sees content starting within ~100-200ms
```

## Best Practices

### 1. Always Use `flush=True` for Real-Time Display

```python
# Good: shows content immediately
async for chunk in agent.stream("Query"):
    print(chunk.delta, end="", flush=True)

# Bad: content may be buffered and appear in batches
async for chunk in agent.stream("Query"):
    print(chunk.delta, end="")  # No flush
```

### 2. Handle Errors Gracefully

```python
# Good: handle interruption
try:
    async for chunk in agent.stream("Query"):
        print(chunk.delta, end="", flush=True)
except Exception as e:
    print(f"\nError: {e}")

# Bad: no error handling
async for chunk in agent.stream("Query"):
    print(chunk.delta, end="", flush=True)  # Crashes silently
```

### 3. Check `finish_reason` for Completion

```python
# Good: explicit completion check
async for chunk in agent.stream("Query"):
    print(chunk.delta, end="", flush=True)
    if chunk.finish_reason == "stop":
        print("\n[Complete]")
        break

# Less clear: rely on loop ending
async for chunk in agent.stream("Query"):
    print(chunk.delta, end="", flush=True)
print("\n[Done]")  # Did it actually finish or error?
```

### 4. Collect Usage on Last Chunk

```python
# Good: only check usage on last chunk
final_chunk = None

async for chunk in agent.stream("Query"):
    final_chunk = chunk
    print(chunk.delta, end="", flush=True)

if final_chunk and final_chunk.usage:
    print(f"Tokens: {final_chunk.usage.total_tokens}")

# Bad: usage is None until last chunk
async for chunk in agent.stream("Query"):
    print(f"Usage: {chunk.usage}")  # Prints None repeatedly
```

### 5. Use Streaming for Long Responses

```python
# Good: stream for interactive experience
async for chunk in agent.stream("Write a 1000-word essay"):
    print(chunk.delta, end="", flush=True)

# Less ideal for long responses: wait for full result
result = agent.run_sync("Write a 1000-word essay")
print(result.output)  # Long wait before any output
```

## Complete Example

```python
import asyncio
from agentweave import Agent, tool

@tool(description="Get word count")
def word_count(text: str) -> int:
    return len(text.split())

async def main():
    agent = Agent(
        name="writer",
        role="Essay writer",
        model="gpt-4o-mini",
        tools=[word_count]
    )

    # Stream a response
    print("Essay:")
    print("-" * 40)

    total_chars = 0
    async for chunk in agent.stream("Write a short essay about AI"):
        print(chunk.delta, end="", flush=True)
        total_chars += len(chunk.delta)

        # Show progress every 200 chars
        if total_chars > 0 and total_chars % 200 == 0:
            print(f" [{total_chars}]", end="\r", flush=True)

    print("\n" + "-" * 40)

    # After streaming completes, usage is available
    if chunk.finish_reason == "stop":
        print(f"\nTokens used: {chunk.usage.total_tokens}")
        print(f"Total characters: {total_chars}")

if __name__ == "__main__":
    asyncio.run(main())
```

## See Also

- [Tools Guide](tools.md) - Use tools with streaming
- [Providers Guide](providers.md) - Stream with different providers
- [Agent Documentation](../api/core.md) - Agent API details
- [Examples](../examples.md) - Complete streaming examples
