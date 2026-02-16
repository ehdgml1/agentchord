# Contributing to AgentWeave

Thank you for your interest in contributing to AgentWeave! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/) for dependency management

### Installation

```bash
# Clone the repository
git clone https://github.com/agentweave/agentweave.git
cd agentweave

# Install dependencies (with all optional extras)
poetry install --extras all

# Install pre-commit hooks
poetry run pre-commit install
```

## Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run benchmarks
make bench
```

## Code Quality

### Linting and Formatting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for lint errors
make lint

# Auto-format code
make format

# Check formatting without changes
make format-check
```

### Type Checking

We use [mypy](https://mypy-lang.org/) for static type analysis:

```bash
make typecheck
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
poetry run pre-commit run --all-files
```

## Project Structure

```
agentweave/
├── core/           # Agent, Workflow, Executor, types
├── errors/         # Exception hierarchy
├── llm/            # LLM providers (OpenAI, Anthropic, Ollama, Gemini)
├── logging/        # Structured logging
├── memory/         # Memory system + persistent stores
├── protocols/      # MCP and A2A protocol support
├── resilience/     # Retry, circuit breaker, timeout
├── telemetry/      # OpenTelemetry + trace collector
├── tools/          # Tool system (@tool decorator)
└── tracking/       # Cost tracking + callbacks
```

## Making Changes

### Branch Naming

- `feat/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Gemini provider support
fix: prevent path traversal in JSONFileStore
docs: update memory system guide
test: add lifecycle management tests
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Ensure all checks pass: `make all`
4. Submit a pull request with a clear description
5. Address review feedback

## Adding a New LLM Provider

1. Create `agentweave/llm/your_provider.py` extending `BaseLLMProvider`
2. Implement `complete()` and `stream()` methods
3. Register prefix in `ProviderRegistry`
4. Add tests in `tests/unit/test_your_provider.py`
5. Add optional dependency in `pyproject.toml`
6. Update documentation

## Reporting Issues

- Use [GitHub Issues](https://github.com/agentweave/agentweave/issues)
- Include Python version, OS, and AgentWeave version
- Provide a minimal reproducible example when possible

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
