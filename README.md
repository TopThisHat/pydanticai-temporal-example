# Deep Research POC

A production-grade proof-of-concept for AI-powered deep research workflows using **pydantic-ai**, **OpenAI**, and **Temporal**, featuring **multi-agent orchestration** with planning, validation, and critique loops.

## 🎯 Features

- **Multi-Agent Architecture**: Specialized agents for planning, validation, critique, and synthesis
- **AI-Powered Research**: Leverages OpenAI GPT-4 via pydantic-ai for structured, iterative research
- **REST API**: Production-ready FastAPI with async/sync endpoints, OpenAPI docs, and dependency injection
- **Validation & Critique Loops**: Automatic quality checks with iterative improvement
- **Citations & Sources**: Automatically collects and displays sources with full citations (URL, title, description)
- **Durable Workflows**: Temporal orchestration for reliable, long-running research tasks
- **Type-Safe**: Strict typing with Pydantic models and mypy enforcement
- **Observable**: Structured logging with structlog throughout
- **Production-Ready**: Comprehensive error handling, retries, and testing

## 🏗️ Architecture

The system uses a multi-agent pipeline where specialized agents work together:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Multi-Agent Research Pipeline                        │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Query Expansion │────▶│ Planning Agent  │────▶│ Research Agent  │
│     Agent       │     │                 │     │   (per task)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
       │                        │                        │
       │   Refines & expands    │   Creates sub-tasks   │   Executes research
       │   the query            │   with dependencies    │   on each task
       │                        │                        │
       │                        │                        ▼
       │                        │              ┌─────────────────┐
       │                        │              │ Validation Agent│◄──┐
       │                        │              └────────┬────────┘   │
       │                        │                       │            │
       │                        │    All parts answered?│            │
       │                        │                       ▼            │
       │                        │              ┌─────────────────┐   │
       │                        │              │ Critique Agent  │   │ Improvement
       │                        │              └────────┬────────┘   │ Loop
       │                        │                       │            │
       │                        │    Quality acceptable?│            │
       │                        │         No ───────────┴────────────┘
       │                        │         Yes
       │                        │                       ▼
       │                        │              ┌─────────────────┐
       │                        └─────────────▶│ Synthesis Agent │
       │                                       └────────┬────────┘
       │                                                │
       └────────────────────────────────────────────────┴─────────────▶ Final Report
```

### Specialized Agents

| Agent | Purpose |
|-------|---------|
| **QueryExpansionAgent** | Refines queries, identifies intent, suggests search terms |
| **PlanningAgent** | Breaks query into sub-tasks with priorities and dependencies |
| **ResearchAgent** | Conducts actual research with web search, Wikipedia, URL fetching |
| **ValidationAgent** | Checks if all query parts are answered, identifies gaps |
| **CritiqueAgent** | Assesses quality, identifies weaknesses, suggests improvements |
| **SynthesisAgent** | Combines findings into comprehensive, well-cited summary |

### System Architecture

```
┌──────────────┐
│   Starter    │ ◄─── Start workflows, send approvals
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Temporal   │ ◄─── Workflow orchestration
│    Server    │      State management
└──────┬───────┘      Signals & queries
       │
       ▼
┌──────────────┐
│    Worker    │ ◄─── Execute workflows
│              │      Run activities
└──────┬───────┘
       │
       ├─────────────────┬─────────────────┐
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Research   │  │  Synthesis   │  │   Approval   │
│   Activity   │  │   Activity   │  │   Activity   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌───────────────────────────────────────────────┐
│         ResearchAgent (pydantic-ai)            │
│              OpenAI GPT-4                      │
└───────────────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.10+
- Temporal server (local or cloud)
- OpenAI API key
- `uv` for dependency management (recommended) or `pip`

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd deep-research-poc

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
# Required: OPENAI_API_KEY
```

### 2. Install Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

For development:
```bash
uv sync --dev
# or
pip install -e ".[dev]"
```

## 🖥️ Running the System

Running the Deep Research POC requires **three terminal windows** running simultaneously:

### Terminal 1: Start the Temporal Server

The Temporal server orchestrates all workflows and maintains state. Start the development server:

```bash
# Start local Temporal development server
temporal server start-dev
```

This starts:
- Temporal server on `localhost:7233`
- Web UI on `http://localhost:8233` (useful for monitoring workflows)

> **Note**: Keep this terminal running. The server must be active for workflows to execute.

### Terminal 2: Start the Worker

The worker connects to Temporal and executes workflows and activities:

```bash
# Using uv (recommended)
uv run python -m deep_research_poc.temporal.worker

# Or using pip-installed package
python -m deep_research_poc.temporal.worker
```

Expected output:
```
🚀 Worker running. Press Ctrl+C to stop.
```

The worker will:
- Connect to Temporal at `localhost:7233`
- Register the `DeepResearchWorkflow` and activities
- Listen on the `deep-research-queue` task queue
- Wait for incoming work

> **Note**: Keep this terminal running. The worker must be active to process research requests.

### Terminal 3: Send Research Requests

With both the Temporal server and worker running, send research requests:

```bash
# Using uv (recommended)
uv run python -m deep_research_poc.starter "What are the latest trends in AI?"

# Or using pip-installed package
python -m deep_research_poc.starter "What are the latest trends in AI?"

# Complex multi-part query example
uv run python -m deep_research_poc.starter "Tell me about the owners of the Dallas Mavs? For each owner, major or minority, include their source of wealth and other investments"
```

The workflow automatically:
- **Expands your query** for better search coverage
- **Plans research tasks** with dependencies
- **Validates findings** to ensure completeness
- **Critiques quality** and triggers additional research if needed
- **Synthesizes results** with proper citations

Expected output:
```
🔬 Starting research: What are the latest trends in AI?
📋 Phases: Query Expansion → Planning → Research → Validation → Critique → Synthesis

================================================================================
📊 RESEARCH COMPLETED
================================================================================
Status: completed
Total Iterations: 5
Duration: 60.23 seconds

📝 Final Summary:
[Research summary with inline citations like [1], [2], etc.]

--------------------------------------------------------------------------------
📚 SOURCES & CITATIONS
--------------------------------------------------------------------------------
[1] Article Title
    Brief description of information used from this source
    URL: https://example.com/article

[2] Another Source
    What information was extracted
    URL: https://example.com/source2
================================================================================
```

### Terminal 4 (Optional): Start the REST API

For programmatic access, start the FastAPI server:

```bash
# Using uv (recommended)
uv run python -m deep_research_poc.api

# Or with hot-reload for development
uv run uvicorn deep_research_poc.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API provides:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Terminal 5 (Optional): Start the Streamlit Web UI

For a user-friendly web interface with real-time status updates:

```bash
# Using uv (recommended)
uv run streamlit run src/deep_research_poc/streamlit_app/app.py

# Or using the module entry point
uv run python -m deep_research_poc.streamlit_app
```

The Streamlit app provides:
- **Interactive Query Form**: Submit research queries with depth options
- **Real-Time Status**: Live progress updates during research
- **Results Visualization**: Comprehensive display of findings, steps, and sources
- **Session Management**: Track and manage active research workflows

Access the app at: **http://localhost:8501**

> **Note**: The Streamlit app requires the FastAPI server (Terminal 4) to be running.

### Quick Reference

| Terminal | Command | Purpose |
|----------|---------|---------|
| 1 | `temporal server start-dev` | Run Temporal orchestration server |
| 2 | `uv run python -m deep_research_poc.temporal.worker` | Execute workflows and activities |
| 3 | `uv run python -m deep_research_poc.starter "query"` | Submit research via CLI |
| 4 | `uv run python -m deep_research_poc.api` | Start REST API server (optional) |
| 5 | `uv run streamlit run src/deep_research_poc/streamlit_app/app.py` | Start Streamlit Web UI (optional) |

#