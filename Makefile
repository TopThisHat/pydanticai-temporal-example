# Makefile for deep-research-poc

.PHONY: help install dev-install format lint type-check test test-cov mutate clean run-worker run-temporal

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

dev-install: ## Install dependencies including dev tools
	uv sync --dev

format: ## Format code with ruff
	uv run ruff format src tests examples

lint: ## Lint code with ruff
	uv run ruff check src tests examples

lint-fix: ## Lint and auto-fix issues
	uv run ruff check --fix src tests examples

type-check: ## Run type checking with mypy
	uv run mypy src/deep_research_poc

test: ## Run tests
	uv run pytest tests -v

mutate: ## Mutation-test the model logic (see docs/property-testing-in-the-age-of-ai.md)
	uv run mutmut run && uv run mutmut results

test-cov: ## Run tests with coverage
	uv run pytest tests --cov=deep_research_poc --cov-report=html --cov-report=term

clean: ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

run-temporal: ## Start Temporal development server
	temporal server start-dev

run-worker: ## Start the research worker
	uv run python -m deep_research_poc.worker

run-example: ## Run example research
	uv run python -m deep_research_poc.starter "What are the key benefits of using type hints in Python?"

check-all: format lint type-check test ## Run all checks (format, lint, type-check, test)
