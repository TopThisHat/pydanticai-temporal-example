# Deep Research POC - AI Coding Agent Instructions

## Project Overview
This is a proof-of-concept for deep research workflows using OpenAI and Temporal with human-in-the-loop capabilities. The architecture combines AI-powered research with durable workflow orchestration.

## Tech Stack & Architecture
- **Temporal**: Workflow orchestration for long-running research tasks with state persistence
- **OpenAI**: AI research agent using GPT-4 (via OpenAI SDK and pydantic-ai)
- **Pydantic**: Type-safe data models and validation (v2+)
- **Python 3.10+**: Strict typing enforced via mypy

## Development Setup

### Environment Configuration
Copy `.env.example` to `.env` and configure:
- `OPENAI_API_KEY`: Required for OpenAI API access
- `TEMPORAL_ADDRESS`: Default `localhost:7233` (assumes local Temporal server)
- `TEMPORAL_TASK_QUEUE`: Queue name for workflow tasks (`deep-research-queue`)
- `HUMAN_APPROVAL_TIMEOUT_MINUTES`: Timeout for human-in-the-loop approval (default: 60)
- `MAX_RESEARCH_ITERATIONS`: Safety limit for research loops (default: 5)

### Dependency Management
Uses `uv` for fast dependency management (note: `uv.lock` present):
```bash
uv sync                    # Install dependencies
uv sync --dev             # Include dev dependencies
```

### Running Temporal Workflows
Requires Temporal server running locally:
```bash
temporal server start-dev  # Start local Temporal dev server
```

## Code Conventions

### Type Safety
- **Strict mypy**: All functions must have type annotations (`disallow_untyped_defs = true`)
- Use Pydantic models for all workflow inputs/outputs and API payloads
- No `Any` types without explicit justification

### Code Style
- **Line length**: 100 characters (Black + Ruff configured)
- **Formatter**: Ruff (replaces Black in this project)
- Run `ruff format` before committing
- Run `ruff check --fix` to auto-fix linting issues

### Testing
- **Framework**: pytest with pytest-asyncio for async tests
- Test Temporal workflows using Temporal's testing utilities
- Mock OpenAI calls in unit tests to avoid API costs

## Workflow Design Patterns

### Human-in-the-Loop Pattern
When implementing approval workflows:
- Use Temporal signals for human input
- Set timeouts via `HUMAN_APPROVAL_TIMEOUT_MINUTES` 
- Always provide fallback behavior on timeout
- Log all approval requests with structlog

### Error Handling in Workflows
- Use Temporal's retry policies for transient failures
- Catch and log OpenAI API errors explicitly
- Respect `MAX_RESEARCH_ITERATIONS` to prevent infinite loops

## Key Integration Points
- **OpenAI SDK**: Used via pydantic-ai wrapper for structured outputs
- **Temporal Activities**: Wrap external API calls (OpenAI) as Temporal activities
- **Structlog**: Use structured logging throughout for observability

## When Adding New Features
1. Define Pydantic models for inputs/outputs first
2. Implement business logic as Temporal activities (for retryability)
3. Compose activities into workflows
4. Add type hints and ensure `mypy --strict` passes
5. Write async tests with pytest-asyncio
