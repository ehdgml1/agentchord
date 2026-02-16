# Agent MCP Tool Binding Implementation

## Summary

Successfully implemented MCP tool binding for Agent nodes in the workflow executor. This allows Agent nodes to use MCP tools at runtime by specifying tool IDs in the `mcpTools` field.

## Changes Made

### 1. Updated `WorkflowExecutor._run_agent` (executor.py:824-851)
- Added call to `_build_agent_tools()` to convert MCP tool IDs to Tool objects
- Pass tools to Agent constructor via `tools` parameter
- Maintains backward compatibility (agents without mcpTools work as before)

### 2. Added `WorkflowExecutor._build_agent_tools` (executor.py:1017-1065)
- Converts list of "serverId:toolName" IDs to agentweave Tool objects
- Validates tool ID format and logs warnings for invalid IDs
- Skips missing tools with warnings instead of failing
- Creates async wrapper functions that call MCPManager.execute_tool
- Uses default args in closure to properly capture loop variables

### 3. Added `WorkflowExecutor._find_mcp_tool` (executor.py:1067-1073)
- Helper to find MCPTool by server_id and tool_name
- Returns None if server or tool not found

### 4. Added `WorkflowExecutor._schema_to_tool_params` (executor.py:1075-1095)
- Converts JSON Schema (from MCP) to ToolParameter list (for agentweave)
- Handles required fields, types, descriptions, defaults, and enums
- Static method for testability

### 5. Updated `MockMCPManager` (conftest.py:105-127)
- Added `_tools` attribute to support tool lookup in tests
- Maintains backward compatibility with existing tests

### 6. Created Test Suite (test_agent_mcp_binding.py)
13 comprehensive tests covering:
- Backward compatibility (agents without mcpTools)
- Valid tool ID conversion
- Invalid format handling
- Missing tool handling
- Schema to parameter conversion
- Tool lookup (found/not found cases)
- Mock mode execution with tools
- Multiple tools
- Partial success scenarios

## Test Results

All 13 new tests pass:
- `test_agent_without_mcp_tools` ✓
- `test_build_agent_tools_valid` ✓
- `test_build_agent_tools_invalid_format` ✓
- `test_build_agent_tools_missing_tool` ✓
- `test_schema_to_tool_params` ✓
- `test_find_mcp_tool_found` ✓
- `test_find_mcp_tool_not_found` ✓
- `test_agent_with_mcp_tools_mock_mode` ✓
- `test_schema_to_tool_params_empty_schema` ✓
- `test_schema_to_tool_params_no_required` ✓
- `test_find_mcp_tool_server_not_found` ✓
- `test_build_agent_tools_multiple_tools` ✓
- `test_build_agent_tools_partial_success` ✓

No regressions in existing tests (245/246 pass, 1 pre-existing failure in unrelated test).

## Design Decisions

### 1. Graceful Degradation
Invalid or missing tool IDs are logged as warnings but don't fail execution. This allows workflows to continue even if some tools are unavailable.

### 2. Closure Variable Capture
Used default arguments (`_sid=server_id, _tn=tool_name`) instead of direct closure to avoid common Python closure pitfall where loop variables are captured by reference.

### 3. Tool Naming
Tools are named as `{server_id}__{tool_name}` to avoid naming conflicts when multiple servers provide tools with the same name.

### 4. Lazy Imports
Maintained existing pattern of lazy importing agentweave modules to avoid circular dependencies.

### 5. Mock Mode Support
Tools are built even in mock mode to ensure the workflow structure is validated, but actual tool execution is mocked.

## Usage Example

```python
# Frontend AgentBlockData
{
  "id": "agent-1",
  "type": "agent",
  "data": {
    "name": "Research Agent",
    "role": "Web researcher",
    "model": "gpt-4o-mini",
    "mcpTools": [
      "fetch:get_url",
      "memory:store_data",
      "search:google_search"
    ]
  }
}
```

The agent will automatically have access to these MCP tools when it runs.

## Files Modified

1. `/Users/ud/Documents/work/agentweave/visual-builder/backend/app/core/executor.py`
   - Added 3 new methods (~80 lines)
   - Modified 1 existing method (_run_agent)

2. `/Users/ud/Documents/work/agentweave/visual-builder/backend/tests/conftest.py`
   - Updated MockMCPManager fixture

3. `/Users/ud/Documents/work/agentweave/visual-builder/backend/tests/test_agent_mcp_binding.py`
   - New file with 13 tests (~300 lines)

## Verification

Run tests with:
```bash
cd backend
python -m pytest tests/test_agent_mcp_binding.py -v
```

All tests pass successfully.
