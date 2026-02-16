.PHONY: help test test-cov test-unit test-integration bench lint format typecheck clean all

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

test:  ## Run all tests
	python -m pytest tests/ -q --tb=short

test-cov:  ## Run tests with coverage
	python -m pytest tests/ --cov=agentweave --cov-report=term-missing --cov-report=html

test-unit:  ## Run unit tests only
	python -m pytest tests/unit/ -q --tb=short

test-integration:  ## Run integration tests only
	python -m pytest tests/integration/ -q --tb=short

bench:  ## Run performance benchmarks
	python -m pytest benchmarks/ -v --tb=short -q

lint:  ## Run linter
	ruff check .

format:  ## Format code
	ruff format .

format-check:  ## Check code formatting
	ruff format --check .

typecheck:  ## Run type checker
	mypy agentweave/ --ignore-missing-imports

clean:  ## Clean build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

all: lint format-check typecheck test  ## Run all checks

# === Build & Publish ===
# NOTE: Prefer publishing via GitHub Actions (gh release create) for OIDC security.
# These targets are for local/emergency use only.

.PHONY: build publish-test publish release version

build: clean  ## Build distribution packages
	poetry build

publish-test: build  ## Publish to TestPyPI
	poetry publish -r testpypi

publish: build  ## Publish to PyPI
	poetry publish

release: clean build  ## Full release (clean + build + publish)
	poetry publish

version:  ## Show current version
	@poetry version
