"""API routes for deep research workflows.

This module defines the REST API endpoints for interacting with
deep research workflows.
"""

from __future__ import annotations

from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, status

from deep_research_poc.api.dependencies import (
    SettingsDep,
    TemporalClientDep,
    TemporalHealthDep,
)
from deep_research_poc.api.schemas import (
    AgentEventResponse,
    AgentEventsResponse,
    ErrorResponse,
    HealthResponse,
    ResearchRequest,
    ResearchResultResponse,
    ResearchStartResponse,
    ResearchStatusResponse,
    ResearchStepResponse,
    SourceResponse,
)
from deep_research_poc.models import (
    ResearchQuery,
    WorkflowInput,
    WorkflowOutput,
)
from deep_research_poc.temporal.workflows import DeepResearchWorkflow

logger = structlog.get_logger()

# Create routers
health_router = APIRouter(tags=["Health"])
research_router = APIRouter(prefix="/research", tags=["Research"])


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health of the API and its dependencies",
)
async def health_check(
    settings: SettingsDep,
    temporal_connected: TemporalHealthDep,
) -> HealthResponse:
    """Check API health and dependencies."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        temporal_connected=temporal_connected,
    )


@research_router.post(
    "",
    response_model=ResearchStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a research workflow",
    description="Start a new deep research workflow with the given query",
    responses={
        202: {"description": "Workflow started successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Temporal unavailable"},
    },
)
async def start_research(
    request: ResearchRequest,
    settings: SettingsDep,
    temporal_client: TemporalClientDep,
) -> ResearchStartResponse:
    """Start a new research workflow.

    The workflow runs asynchronously. Use the returned workflow_id
    to check status or retrieve results.
    """
    workflow_id = f"research-{uuid4()}"

    research_query = ResearchQuery(
        query=request.query,
        max_iterations=request.max_iterations,
        depth=request.depth,
        metadata=request.metadata,
    )

    workflow_input = WorkflowInput(
        research_query=research_query,
        workflow_id=workflow_id,
    )

    logger.info(
        "starting_research_workflow",
        workflow_id=workflow_id,
        query=request.query[:100],
        depth=request.depth,
        max_iterations=request.max_iterations,
    )

    try:
        handle = await temporal_client.start_workflow(
            DeepResearchWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        logger.info(
            "workflow_started",
            workflow_id=handle.id,
            run_id=handle.result_run_id,
        )

        return ResearchStartResponse(
            workflow_id=workflow_id,
            status="started",
            message="Research workflow started successfully. "
            f"Use GET /research/{workflow_id} to check status.",
        )

    except Exception as e:
        logger.error(
            "workflow_start_failed",
            workflow_id=workflow_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to start workflow: {e}",
        ) from e


@research_router.get(
    "/{workflow_id}/status",
    response_model=ResearchStatusResponse,
    summary="Get workflow status",
    description="Get the current status of a research workflow",
    responses={
        200: {"description": "Workflow status retrieved"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def get_research_status(
    workflow_id: str,
    temporal_client: TemporalClientDep,
) -> ResearchStatusResponse:
    """Get the current status of a research workflow."""
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
        status_data = await handle.query(DeepResearchWorkflow.get_status)

        logger.info(
            "workflow_status_queried",
            workflow_id=workflow_id,
            status=status_data.get("status"),
        )

        return ResearchStatusResponse(
            workflow_id=workflow_id,
            status=str(status_data.get("status", "unknown")),
            current_phase=str(status_data.get("current_phase"))
            if status_data.get("current_phase")
            else None,
            research_steps=int(status_data.get("research_steps", 0)),
            validation_iterations=int(status_data.get("validation_iterations", 0)),
        )

    except Exception as e:
        logger.warning(
            "workflow_status_query_failed",
            workflow_id=workflow_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found or not accessible: {workflow_id}",
        ) from e


@research_router.get(
    "/{workflow_id}/events",
    response_model=AgentEventsResponse,
    summary="Get agent events",
    description="Get agent events for chat-style display of workflow progress",
    responses={
        200: {"description": "Agent events retrieved"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def get_agent_events(
    workflow_id: str,
    temporal_client: TemporalClientDep,
) -> AgentEventsResponse:
    """Get agent events for a workflow for chat-style display."""
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
        events_data = await handle.query(DeepResearchWorkflow.get_agent_events)

        logger.info(
            "agent_events_queried",
            workflow_id=workflow_id,
            num_events=len(events_data),
        )

        events = [
            AgentEventResponse(
                event_id=e["event_id"],
                timestamp=e["timestamp"],
                event_type=e["event_type"],
                agent_name=e["agent_name"],
                message=e["message"],
                details=e.get("details", {}),
                phase=e.get("phase", ""),
            )
            for e in events_data
        ]

        return AgentEventsResponse(
            workflow_id=workflow_id,
            events=events,
            total_events=len(events),
        )

    except Exception as e:
        logger.warning(
            "agent_events_query_failed",
            workflow_id=workflow_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found or not accessible: {workflow_id}",
        ) from e


@research_router.get(
    "/{workflow_id}",
    response_model=ResearchResultResponse,
    summary="Get research results",
    description="Get the complete results of a finished research workflow",
    responses={
        200: {"description": "Research results retrieved"},
        202: {"model": ResearchStatusResponse, "description": "Workflow still running"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def get_research_result(
    workflow_id: str,
    temporal_client: TemporalClientDep,
) -> ResearchResultResponse:
    """Get the complete results of a research workflow.

    If the workflow is still running, returns 202 with current status.
    """
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)

        # First check if workflow is complete
        status_data = await handle.query(DeepResearchWorkflow.get_status)
        current_status = str(status_data.get("status", ""))

        if current_status not in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail={
                    "message": "Workflow still in progress",
                    "workflow_id": workflow_id,
                    "status": current_status,
                    "current_phase": status_data.get("current_phase"),
                },
            )

        # Handle failed workflows
        if current_status == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Workflow failed",
                    "workflow_id": workflow_id,
                    "status": current_status,
                    "error": status_data.get("error", "Unknown error"),
                },
            )

        # Get the result (only for completed workflows)
        result_data = await handle.result()
        # Temporal returns dicts, so we need to parse into the Pydantic model
        if isinstance(result_data, dict):
            result = WorkflowOutput.model_validate(result_data)
        else:
            result = result_data

        logger.info(
            "workflow_result_retrieved",
            workflow_id=workflow_id,
            status=result.result.status.value,
        )

        # Convert to response model
        steps = [
            ResearchStepResponse(
                step_id=str(step.step_id),
                iteration=step.iteration,
                question=step.question,
                findings=step.findings,
                confidence=step.confidence,
                sources=[SourceResponse.from_source(s) for s in step.sources],
                timestamp=step.timestamp,
            )
            for step in result.result.steps
        ]

        sources = [
            SourceResponse.from_source(s) for s in result.result.all_sources
        ]

        return ResearchResultResponse(
            workflow_id=workflow_id,
            query=result.result.query,
            status=result.result.status,
            final_summary=result.result.final_summary,
            total_iterations=result.result.total_iterations,
            duration_seconds=result.duration_seconds,
            steps=steps,
            sources=sources,
            started_at=result.result.started_at,
            completed_at=result.result.completed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "workflow_result_query_failed",
            workflow_id=workflow_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving workflow result: {type(e).__name__}: {e}",
        ) from e


@research_router.post(
    "/sync",
    response_model=ResearchResultResponse,
    summary="Run synchronous research",
    description="Start a research workflow and wait for completion",
    responses={
        200: {"description": "Research completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Temporal unavailable"},
        504: {"model": ErrorResponse, "description": "Research timed out"},
    },
)
async def run_research_sync(
    request: ResearchRequest,
    settings: SettingsDep,
    temporal_client: TemporalClientDep,
) -> ResearchResultResponse:
    """Run research synchronously and wait for results.

    This endpoint blocks until research is complete. For long-running
    research, use the async POST /research endpoint instead.
    """
    workflow_id = f"research-{uuid4()}"

    research_query = ResearchQuery(
        query=request.query,
        max_iterations=request.max_iterations,
        depth=request.depth,
        metadata=request.metadata,
    )

    workflow_input = WorkflowInput(
        research_query=research_query,
        workflow_id=workflow_id,
    )

    logger.info(
        "starting_sync_research_workflow",
        workflow_id=workflow_id,
        query=request.query[:100],
        depth=request.depth,
    )

    try:
        handle = await temporal_client.start_workflow(
            DeepResearchWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        # Wait for result
        result: WorkflowOutput = await handle.result()

        logger.info(
            "sync_workflow_completed",
            workflow_id=workflow_id,
            status=result.result.status.value,
            duration=result.duration_seconds,
        )

        # Convert to response model
        steps = [
            ResearchStepResponse(
                step_id=str(step.step_id),
                iteration=step.iteration,
                question=step.question,
                findings=step.findings,
                confidence=step.confidence,
                sources=[SourceResponse.from_source(s) for s in step.sources],
                timestamp=step.timestamp,
            )
            for step in result.result.steps
        ]

        sources = [
            SourceResponse.from_source(s) for s in result.result.all_sources
        ]

        return ResearchResultResponse(
            workflow_id=workflow_id,
            query=result.result.query,
            status=result.result.status,
            final_summary=result.result.final_summary,
            total_iterations=result.result.total_iterations,
            duration_seconds=result.duration_seconds,
            steps=steps,
            sources=sources,
            started_at=result.result.started_at,
            completed_at=result.result.completed_at,
        )

    except Exception as e:
        logger.error(
            "sync_workflow_failed",
            workflow_id=workflow_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Research workflow failed: {e}",
        ) from e
