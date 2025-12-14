"""Script to start a research workflow.

This module provides CLI and programmatic interfaces to start and interact
with deep research workflows using the multi-agent architecture.

Usage:
    python -m deep_research_poc.starter "your research query"
    python -m deep_research_poc.starter --status <workflow_id>
"""

from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

import structlog
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from deep_research_poc.config import get_settings
from deep_research_poc.logging_config import configure_logging
from deep_research_poc.models import (
    ResearchQuery,
    WorkflowInput,
    WorkflowOutput,
)
from deep_research_poc.temporal.workflows import DeepResearchWorkflow

logger = structlog.get_logger()


async def start_research_workflow(
    query: str,
    max_iterations: int = 5,
    depth: str = "deep",
) -> WorkflowOutput:
    """Start a new research workflow.

    Uses the multi-agent architecture with planning and validation
    loops for comprehensive research.

    Args:
        query: The research question to investigate
        max_iterations: Maximum research iterations (1-10)
        depth: Research depth - 'quick', 'standard', or 'deep'

    Returns:
        WorkflowOutput with complete research results
    """
    settings = get_settings()

    research_query = ResearchQuery(
        query=query,
        max_iterations=max_iterations,
        depth=depth,
    )

    workflow_id = f"research-{uuid4()}"

    workflow_input = WorkflowInput(
        research_query=research_query,
        workflow_id=workflow_id,
    )

    logger.info(
        "starting_workflow",
        workflow_id=workflow_input.workflow_id,
        query=query[:100],
        max_iterations=max_iterations,
        depth=depth,
    )

    # Connect to Temporal with Pydantic data converter
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=pydantic_data_converter,
    )

    # Start the multi-agent workflow
    handle = await client.start_workflow(
        DeepResearchWorkflow.run,
        workflow_input,
        id=workflow_input.workflow_id,
        task_queue=settings.temporal_task_queue,
    )

    logger.info(
        "workflow_started",
        workflow_id=handle.id,
        run_id=handle.result_run_id,
    )

    # Wait for result
    result = await handle.result()

    logger.info(
        "workflow_completed",
        workflow_id=handle.id,
        status=result.result.status.value,
        duration=result.duration_seconds,
    )

    return result


async def query_workflow_status(workflow_id: str) -> dict[str, object]:
    """Query the current status of a workflow.

    Args:
        workflow_id: The workflow ID to query

    Returns:
        Status information dictionary
    """
    settings = get_settings()

    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=pydantic_data_converter,
    )

    handle = client.get_workflow_handle(workflow_id)
    status = await handle.query(DeepResearchWorkflow.get_status)

    logger.info("workflow_status_queried", workflow_id=workflow_id, status=status)

    return status  # type: ignore[return-value]


async def main() -> None:
    """CLI entry point for research workflows."""
    settings = get_settings()
    configure_logging(settings.log_level)

    if len(sys.argv) < 2:
        print("Deep Research POC - AI-powered multi-agent research with Temporal")
        print()
        print("Usage:")
        print("  python -m deep_research_poc.starter <query>")
        print("  python -m deep_research_poc.starter --status <workflow_id>")
        print()
        print("Options:")
        print("  --status    Query the status of a running workflow")
        print()
        print("Examples:")
        print('  python -m deep_research_poc.starter "What is quantum computing?"')
        print('  python -m deep_research_poc.starter "Who are the owners of the Dallas Mavs?"')
        print("  python -m deep_research_poc.starter --status research-abc123")
        sys.exit(1)

    if sys.argv[1] == "--status":
        if len(sys.argv) < 3:
            print("Usage: python -m deep_research_poc.starter --status <workflow_id>")
            sys.exit(1)

        workflow_id = sys.argv[2]
        status = await query_workflow_status(workflow_id)

        print(f"\nWorkflow Status: {workflow_id}")
        print(f"Status: {status.get('status')}")
        print(f"Current Phase: {status.get('current_phase')}")
        print(f"Research Steps: {status.get('research_steps')}")
        print(f"Validation Iterations: {status.get('validation_iterations')}")

    else:
        # Start new research
        query = " ".join(sys.argv[1:])
        print(f"\n🔬 Starting research: {query}")
        print("📋 Phases: Query Expansion → Planning → Research → Validation → Synthesis\n")

        result = await start_research_workflow(
            query=query,
            max_iterations=5,
            depth="deep",
        )

        print("\n" + "=" * 80)
        print("📊 RESEARCH COMPLETED")
        print("=" * 80)
        print(f"Status: {result.result.status.value}")
        print(f"Total Iterations: {result.result.total_iterations}")
        print(f"Duration: {result.duration_seconds:.2f} seconds")
        print(f"\n📝 Final Summary:\n{result.result.final_summary}")
        
        # Display sources/citations
        print("\n" + "-" * 80)
        print("📚 SOURCES & CITATIONS")
        print("-" * 80)
        print(result.result.get_formatted_citations())
        print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
