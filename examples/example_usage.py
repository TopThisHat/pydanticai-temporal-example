"""Example script demonstrating programmatic usage of the research system."""

import asyncio

from deep_research_poc.models import ResearchQuery, WorkflowInput
from deep_research_poc.starter import (
    query_workflow_status,
    send_approval,
    start_research_workflow,
)


async def example_basic_research() -> None:
    """Example: Basic research without approval."""
    print("\n=== Example 1: Basic Research (No Approval) ===\n")

    result = await start_research_workflow(
        query="What are the key differences between Python and JavaScript?",
        max_iterations=2,
        require_approval=False,
    )

    print(f"Status: {result.result.status}")
    print(f"Iterations: {result.result.total_iterations}")
    print(f"\nSummary:\n{result.result.final_summary}")


async def example_research_with_approval() -> None:
    """Example: Research with human approval required."""
    print("\n=== Example 2: Research with Approval ===\n")

    # Note: This will wait for approval, so it's meant to be run
    # with the approval script in another terminal

    result = await start_research_workflow(
        query="What are the benefits of using Temporal for workflows?",
        max_iterations=3,
        require_approval=True,
    )

    print(f"Status: {result.result.status}")
    print(f"Approvals received: {len(result.result.approval_responses)}")


async def example_query_status() -> None:
    """Example: Query workflow status."""
    print("\n=== Example 3: Query Workflow Status ===\n")

    # Replace with actual workflow ID
    workflow_id = "research-example-123"

    try:
        status = await query_workflow_status(workflow_id)
        print(f"Workflow: {workflow_id}")
        print(f"Status: {status}")
    except Exception as e:
        print(f"Could not query workflow: {e}")


async def example_send_approval() -> None:
    """Example: Send approval programmatically."""
    print("\n=== Example 4: Send Approval Programmatically ===\n")

    # Replace with actual workflow and request IDs
    workflow_id = "research-example-123"
    request_id = "550e8400-e29b-41d4-a716-446655440000"

    try:
        await send_approval(
            workflow_id=workflow_id,
            request_id=request_id,
            approved=True,
            feedback="Research looks comprehensive!",
        )
        print("Approval sent successfully")
    except Exception as e:
        print(f"Could not send approval: {e}")


async def example_custom_workflow() -> None:
    """Example: Advanced usage with custom configuration."""
    print("\n=== Example 5: Custom Configuration ===\n")

    from temporalio.client import Client

    from deep_research_poc.config import get_settings
    from deep_research_poc.workflows import DeepResearchWorkflow

    settings = get_settings()

    # Create custom research query with metadata
    research_query = ResearchQuery(
        query="What are the best practices for microservices architecture?",
        max_iterations=5,
        require_human_approval=True,
        metadata={
            "department": "engineering",
            "project": "system-redesign",
            "priority": "high",
        },
    )

    workflow_input = WorkflowInput(
        research_query=research_query,
        workflow_id="research-microservices-2024",
    )

    # Connect to Temporal
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )

    # Start workflow with custom settings
    handle = await client.start_workflow(
        DeepResearchWorkflow.run,
        workflow_input,
        id=workflow_input.workflow_id,
        task_queue=settings.temporal_task_queue,
    )

    print(f"Workflow started: {handle.id}")
    print(f"Run ID: {handle.result_run_id}")

    # Can query status or wait for completion
    # result = await handle.result()


async def main() -> None:
    """Run examples."""
    print("Deep Research POC - Examples")
    print("=" * 60)

    # Uncomment the example you want to run
    # await example_basic_research()
    # await example_research_with_approval()
    # await example_query_status()
    # await example_send_approval()
    # await example_custom_workflow()

    print("\nNote: Uncomment examples in main() to run them")


if __name__ == "__main__":
    asyncio.run(main())
