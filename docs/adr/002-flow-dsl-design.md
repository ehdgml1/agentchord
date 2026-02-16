# ADR-002: Use String-based Flow DSL for Workflow Orchestration

## Status
Accepted

## Context

AgentWeave workflows need to define execution order for multiple agents. We evaluated several approaches used by existing frameworks:

**Alternatives considered**:

1. **LangGraph-style Graph API**
   ```python
   graph = StateGraph()
   graph.add_node("researcher", researcher_agent)
   graph.add_node("writer", writer_agent)
   graph.add_edge("researcher", "writer")
   graph.set_entry_point("researcher")
   ```
   - **Pros**: Explicit, supports conditional edges, visualizable
   - **Cons**: Verbose, high learning curve, requires state management

2. **CrewAI-style Process Enum**
   ```python
   crew = Crew(agents=[...], process=Process.SEQUENTIAL)
   ```
   - **Pros**: Simple for basic cases
   - **Cons**: Limited to sequential/hierarchical, no custom flow

3. **Prefect/Airflow-style Task Dependencies**
   ```python
   @task
   def research(): ...
   @task
   def write(): ...
   research() >> write()
   ```
   - **Pros**: Pythonic, familiar to data engineers
   - **Cons**: Requires decorator framework, stateful execution context

4. **String-based DSL** (chosen)
   ```python
   Workflow(agents=[...], flow="researcher -> writer")
   Workflow(agents=[...], flow="A -> [B, C] -> D")
   ```

**Requirements**:
- Intuitive for 80% use case: sequential and parallel execution
- Low learning curve (single string format)
- No runtime state graph management
- Support common patterns without conditional logic (YAGNI: we have no evidence users need `if/else` yet)

## Decision

We implemented a **regex-based Flow DSL parser** with three primitives:

### Syntax

```
sequential  := agent_name "->" agent_name
parallel    := "[" agent_name ("," agent_name)* "]"
composite   := sequential | parallel | (sequential "->" parallel) | ...
```

**Examples**:
- Sequential: `"A -> B -> C"`
- Parallel: `"[A, B, C]"`
- Mixed: `"researcher -> [analyzer, summarizer] -> writer"`

### Implementation

**FlowParser** (`workflow.py:32-133`):

```python
class FlowParser:
    ARROW_PATTERN = re.compile(r"\s*->\s*")
    PARALLEL_PATTERN = re.compile(r"\[([^\]]+)\]")

    def parse(self, flow: str, available_agents: list[str],
              merge_strategy: MergeStrategy) -> list[BaseExecutor]:
        parts = self.ARROW_PATTERN.split(flow.strip())
        steps = []
        for part in parts:
            executor = self._parse_part(part, available_agents, merge_strategy)
            steps.append(executor)
        return steps

    def _parse_part(self, part: str, available_agents, merge_strategy):
        parallel_match = self.PARALLEL_PATTERN.match(part)
        if parallel_match:
            return self._parse_parallel(parallel_match.group(1), ...)
        return self._parse_single(part, available_agents)
```

**Executor pattern** (`executor.py:32-243`):
- `SingleAgentExecutor`: Executes one agent
- `SequentialExecutor`: Chains agents with output piping
- `ParallelExecutor`: Runs agents concurrently via `asyncio.gather()`
- `CompositeExecutor`: Composes executors sequentially

**Merge strategies** for parallel execution (`executor.py:23-29`):
```python
class MergeStrategy(str, Enum):
    CONCAT = "concat"              # "resultA resultB"
    CONCAT_NEWLINE = "concat_newline"  # "resultA\n\nresultB"
    FIRST = "first"                # "resultA"
    LAST = "last"                  # "resultB"
```

### Example Usage

```python
workflow = Workflow(
    agents=[researcher, analyzer, summarizer, writer],
    flow="researcher -> [analyzer, summarizer] -> writer",
    merge_strategy=MergeStrategy.CONCAT_NEWLINE
)
result = await workflow.run("Research AI trends")
```

**Execution flow**:
1. `researcher` runs with input `"Research AI trends"`
2. `analyzer` and `summarizer` run in parallel with `researcher.output`
3. Outputs merged: `analyzer.output + "\n\n" + summarizer.output`
4. `writer` runs with merged output
5. Return `writer.output`

### Error Handling

```python
# workflow.py:69-84
if not flow or not flow.strip():
    raise InvalidFlowError(flow, "Flow string cannot be empty")

for name in agent_names:
    if name not in available_agents:
        raise AgentNotFoundInFlowError(name, available_agents)
```

**Validation at parse time**:
- Empty flow strings rejected
- Unknown agent names rejected (fail-fast)
- Syntax errors surface immediately (no deferred runtime errors)

## Consequences

### Positive
- **Low learning curve**: One-line string format, no API docs needed
- **Declarative**: Flow is data, can be stored/loaded from config files
- **Composable**: Executors are immutable and reusable
- **Type-safe**: mypy validates executor protocol compliance
- **No graph state**: Stateless parsing eliminates cycle detection overhead

### Negative
- **No conditional logic**: Cannot express `if condition: A else: B`
  - **Mitigation**: For conditional flows, users can implement custom executors or use Python control flow:
    ```python
    flow = "A -> B" if condition else "A -> C"
    ```
- **Limited expressiveness**: No loops, dynamic branching, or error recovery paths
  - **YAGNI**: We found no user requests for these features during initial design
- **Regex parsing fragility**: Syntax errors (e.g., `"A -> [B, C"`) fail at parse time, but error messages may be cryptic
- **No cycle detection**: Parser doesn't validate DAG constraints (though sequential/parallel patterns naturally avoid cycles)

### Neutral
- **Arrow syntax**: `->` is intuitive but conflicts with Python's type hints syntax (only in docstrings, not a runtime issue)
- **Whitespace sensitivity**: `"A->B"` and `"A -> B"` are equivalent (regex strips whitespace), but `"[ A, B ]"` and `"[A,B]"` are also equivalent
- **No visualization**: Unlike LangGraph, we don't generate flow diagrams (users must infer from string)

## Future Considerations

If conditional logic becomes a frequent request, potential extensions:

1. **Conditional syntax**: `"A -> (condition ? B : C) -> D"`
2. **Nested workflows**: `"A -> workflow(flow2) -> B"`
3. **Error edges**: `"A -error-> fallback_agent"`

**Decision criteria** for adding these:
- Wait for 10+ user requests
- Ensure syntax remains single-line compatible
- Maintain backward compatibility with existing flows

## References
- Implementation: `agentweave/core/workflow.py`, `agentweave/core/executor.py`
- Tests: `agentweave/tests/unit/core/test_workflow.py` (43 tests), `agentweave/tests/integration/test_workflow_e2e.py` (16 tests)
- Comparison: LangGraph (400 LOC for graph state), CrewAI Process (3 modes), Prefect (DAG builder)
