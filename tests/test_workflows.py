"""Tests for Temporal workflows."""

from datetime import timedelta
from uuid import uuid4

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from deep_research_poc.temporal.activities import (
    conduct_research_activity,
    synthesize_findings_activity,
)
from deep_research_poc.models import (
    ResearchQuery,
    ResearchStatus,
    WorkflowInput,
)
from deep_research_poc.temporal.workflows import DeepResearchWorkflow


@pytest.mark.asyncio
async def test_workflow_basic_execution() -> None:
    """Test basic workflow execution."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[DeepResearchWorkflow],
            activities=[
                conduct_research_activity,
                synthesize_findings_activity,
            ],
        ):
            workflow_input = WorkflowInput(
                research_query=ResearchQuery(
                    query="What is Python programming?",
                    max_iterations=2,
                    depth="quick",
                ),
                workflow_id=f"test-{uuid4()}",
            )

            result = await env.client.execute_workflow(
                DeepResearchWorkflow.run,
                workflow_input,
                id=workflow_input.workflow_id,
                task_queue="test-queue",
                execution_timeout=timedelta(minutes=5),
            )

            assert result.workflow_id == workflow_input.workflow_id
            assert result.result.status in [ResearchStatus.COMPLETED, ResearchStatus.FAILED]
            assert result.result.total_iterations > 0
            assert len(result.result.steps) > 0


@pytest.mark.asyncio
async def test_workflow_status_query() -> None:
    """Test querying workflow status."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[DeepResearchWorkflow],
            activities=[
                conduct_research_activity,
                synthesize_findings_activity,
            ],
        ):
            workflow_input = WorkflowInput(
                research_query=ResearchQuery(
                    query="Test query",
                    max_iterations=1,
                    depth="quick",
                ),
                workflow_id=f"test-{uuid4()}",
            )

            handle = await env.client.start_workflow(
                DeepResearchWorkflow.run,
                workflow_input,
                id=workflow_input.workflow_id,
                task_queue="test-queue",
            )

            status = await handle.query(DeepResearchWorkflow.get_status)

            # Verify status structure
            assert "status" in status
            assert "current_iteration" in status
            assert "total_steps" in status


@pytest.mark.asyncio
async def test_workflow_max_iterations() -> None:
    """Test that workflow respects max iterations limit."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[DeepResearchWorkflow],
            activities=[
                conduct_research_activity,
                synthesize_findings_activity,
            ],
        ):
            max_iter = 3
            workflow_input = WorkflowInput(
                research_query=ResearchQuery(
                    query="Test max iterations",
                    max_iterations=max_iter,
                    depth="standard",
                ),
                workflow_id=f"test-{uuid4()}",
            )

            result = await env.client.execute_workflow(
                DeepResearchWorkflow.run,
                workflow_input,
                id=workflow_input.workflow_id,
                task_queue="test-queue",
                execution_timeout=timedelta(minutes=5),
            )

            # Should not exceed max iterations
            assert result.result.total_iterations <= max_iter


@pytest.mark.asyncio
async def test_workflow_depth_settings() -> None:
    """Test that depth parameter affects iterations."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[DeepResearchWorkflow],
            activities=[
                conduct_research_activity,
                synthesize_findings_activity,
            ],
        ):
            # Quick depth should have max 1 iteration
            workflow_input = WorkflowInput(
                research_query=ResearchQuery(
                    query="Quick test",
                    depth="quick",
                ),
                workflow_id=f"test-{uuid4()}",
            )

            result = await env.client.execute_workflow(
                DeepResearchWorkflow.run,
                workflow_input,
                id=workflow_input.workflow_id,
                task_queue="test-queue",
                execution_timeout=timedelta(minutes=5),
            )

            # Quick mode should complete in 1 iteration
            assert result.result.total_iterations == 1


@pytest.mark.asyncio
async def test_workflow_get_steps_query() -> None:
    """Test querying completed research steps."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[DeepResearchWorkflow],
            activities=[
                conduct_research_activity,
                synthesize_findings_activity,
            ],
        ):
            workflow_input = WorkflowInput(
                research_query=ResearchQuery(
                    query="Test steps query",
                    max_iterations=2,
                    depth="quick",
                ),
                workflow_id=f"test-{uuid4()}",
            )

            result = await env.client.execute_workflow(
                DeepResearchWorkflow.run,
                workflow_input,
                id=workflow_input.workflow_id,
                task_queue="test-queue",
                execution_timeout=timedelta(minutes=5),
            )

            # Verify we have steps
            assert len(result.result.steps) > 0
            for step in result.result.steps:
                assert step.iteration >= 1
                assert step.question
                assert step.findings
                assert 0.0 <= step.confidence <= 1.0
