# Phase 1 Tests

Comprehensive test suite for Phase 1 features: scheduling, mock mode, and resume execution.

## Test Files

### 1. test_scheduler.py
Tests for workflow scheduling functionality.

**Test Cases:**
- `test_add_cron_schedule`: Add schedule and verify in DB
- `test_remove_schedule`: Remove schedule
- `test_schedule_execution`: Verify scheduled workflow runs
- `test_disable_enable_schedule`: Toggle enabled status
- `test_invalid_cron_expression`: Reject invalid expressions
- `test_timezone_handling`: Verify timezone-aware scheduling
- `test_next_run_calculation`: Verify next_run_at is correct

### 2. test_mock_mode.py
Tests for mock execution mode.

**Test Cases:**
- `test_mock_mode_no_network`: Mock mode makes no external calls
- `test_mock_agent_output`: Agent node returns mock response
- `test_mock_tool_output`: MCP tool returns mock response
- `test_mock_custom_response`: Custom mockResponse is used
- `test_mock_condition_always_true`: Condition takes true path
- `test_mock_mode_fast`: Mock execution completes quickly
- `test_mock_vs_full_mode`: Compare mock and full mode
- `test_mock_preserves_workflow_structure`: Respects node order
- `test_mock_mode_with_parameters`: Handles parameters correctly

### 3. test_resume.py
Tests for pause and resume execution.

**Test Cases:**
- `test_pause_and_resume`: Pause execution, resume from checkpoint
- `test_resume_preserves_context`: Context is restored correctly
- `test_resume_from_specific_node`: Start from given node
- `test_resume_after_failure`: Resume after node failure
- `test_checkpoint_saved_before_each_node`: Verify checkpoint saved
- `test_checkpoint_lifecycle`: Save and cleanup lifecycle
- `test_resume_nonexistent_execution`: Error on non-existent execution
- `test_resume_updates_checkpoint`: Checkpoints update during resume
- `test_parallel_checkpoint_safety`: Concurrent saves don't conflict

### 4. test_execution_service.py
Tests for execution service layer.

**Test Cases:**
- `test_start_execution`: Start new execution
- `test_start_execution_nonexistent_workflow`: Error handling
- `test_stop_execution`: Stop running execution
- `test_stop_nonexistent_execution`: Returns False
- `test_stop_completed_execution`: Can't stop completed
- `test_resume_execution`: Resume paused execution
- `test_resume_nonexistent_execution`: Error handling
- `test_resume_non_paused_execution`: Can't resume non-paused
- `test_get_execution_logs`: Retrieve node logs
- `test_get_logs_nonexistent_execution`: Error handling
- `test_get_logs_empty`: Handle empty logs

### 5. conftest.py
Shared fixtures for all tests.

**Fixtures:**
- `event_loop`: Async event loop
- `db_engine`: Test database engine
- `db_session`: Database session
- `mock_mcp_manager`: Mock MCP manager
- `secret_store`: Encrypted secret store
- `state_store`: Execution state store
- `executor`: Workflow executor
- `sample_workflow`: 5-node test workflow
- `simple_workflow`: 2-node test workflow

## Running Tests

### Run All Tests
```bash
# From backend directory
pytest tests/ -v

# Or use the runner script
python tests/run_tests.py
```

### Run Specific Test File
```bash
pytest tests/test_scheduler.py -v
pytest tests/test_mock_mode.py -v
pytest tests/test_resume.py -v
pytest tests/test_execution_service.py -v
```

### Run Specific Test
```bash
pytest tests/test_scheduler.py::test_add_cron_schedule -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=term-missing
pytest tests/ --cov=app --cov-report=html
```

## Requirements

All dependencies are in `requirements.txt`:

```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
croniter>=1.4.0
```

## Test Database

Tests use an in-memory SQLite database (`sqlite+aiosqlite:///:memory:`) that is created fresh for each test session and cleaned up automatically.

## Environment Variables

For `secret_store` tests, a temporary `SECRET_KEY` is auto-generated. For production, set:

```bash
export SECRET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
```

## Test Architecture

### Async Testing
All tests are async-compatible using `pytest-asyncio`. Tests use the `@pytest.mark.asyncio` decorator.

### Database Fixtures
Database fixtures (`db_engine`, `db_session`) are scoped to each test function, ensuring isolation.

### Mock Components
- `MockMCPManager`: Simulates MCP tool execution without network calls
- `MockDB`: Provides database interface for secret_store and state_store

### Workflow Fixtures
- `sample_workflow`: 5-node workflow for comprehensive testing
- `simple_workflow`: 2-node workflow for quick tests

## Expected Results

All tests should pass with:
- No import errors
- No database errors
- All assertions passing
- Coverage > 70% for new Phase 1 code

## Troubleshooting

### Import Errors
Ensure agentweave is installed:
```bash
cd /Users/ud/Documents/work/agentweave
pip install -e .
```

### Database Errors
Check that SQLAlchemy async dependencies are installed:
```bash
pip install aiosqlite sqlalchemy[asyncio]
```

### Async Errors
Ensure pytest-asyncio is installed and configured:
```bash
pip install pytest-asyncio
```

## Coverage Goals

Target coverage for Phase 1 components:
- `app/core/executor.py`: > 80%
- `app/models/schedule.py`: > 90%
- `app/models/execution.py`: > 90%
- Scheduler implementation: > 75%
- Service layer: > 80%

## Next Steps

After all tests pass:
1. Run coverage report: `pytest tests/ --cov=app --cov-report=html`
2. Review uncovered lines in `htmlcov/index.html`
3. Add additional edge case tests if coverage < 70%
4. Proceed to Phase 2 implementation
