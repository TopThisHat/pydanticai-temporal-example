"""API request and response schemas.

These Pydantic models define the API contract for the deep research endpoints.
They follow OpenAPI best practices and provide clear documentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from deep_research_poc.models import AgentEventType, ResearchStatus, Source


class AgentEventResponse(BaseModel):
    """An agent event for chat-style display."""

    event_id: str = Field(
        ...,
        description="Unique event identifier",
    )
    timestamp: datetime = Field(
        ...,
        description="When this event occurred",
    )
    event_type: AgentEventType = Field(
        ...,
        description="Type of event",
    )
    agent_name: str = Field(
        ...,
        description="Name of the agent that generated this event",
    )
    message: str = Field(
        ...,
        description="Human-readable message describing the event",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event details",
    )
    phase: str = Field(
        default="",
        description="Current workflow phase when event occurred",
    )


class AgentEventsResponse(BaseModel):
    """Response containing agent events."""

    workflow_id: str = Field(
        ...,
        description="Workflow identifier",
    )
    events: list[AgentEventResponse] = Field(
        default_factory=list,
        description="List of agent events in chronological order",
    )
    total_events: int = Field(
        ...,
        description="Total number of events",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(
        ...,
        description="Service health status",
        examples=["healthy"],
    )
    version: str = Field(
        ...,
        description="API version",
        examples=["1.0.0"],
    )
    temporal_connected: bool = Field(
        ...,
        description="Whether Temporal server is reachable",
    )


class ResearchRequest(BaseModel):
    """Request to start a new research workflow."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The research question or topic to investigate",
        examples=["Who are the owners of the Dallas Mavericks?"],
    )
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of research iterations",
    )
    depth: str = Field(
        default="standard",
        pattern="^(quick|standard|deep)$",
        description="Research depth: 'quick' (1 iter), 'standard' (3 iter), 'deep' (5+ iter)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for tracking and filtering",
    )


class ResearchStartResponse(BaseModel):
    """Response when a research workflow is started."""

    workflow_id: str = Field(
        ...,
        description="Unique identifier for the started workflow",
        examples=["research-550e8400-e29b-41d4-a716-446655440000"],
    )
    status: str = Field(
        ...,
        description="Initial workflow status",
        examples=["started"],
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
        examples=["Research workflow started successfully"],
    )


class ResearchStatusResponse(BaseModel):
    """Response with current workflow status."""

    workflow_id: str = Field(
        ...,
        description="Workflow identifier",
    )
    status: str = Field(
        ...,
        description="Current workflow status",
    )
    current_phase: str | None = Field(
        None,
        description="Current phase of research",
    )
    research_steps: int = Field(
        default=0,
        description="Number of research steps completed",
    )
    validation_iterations: int = Field(
        default=0,
        description="Number of validation iterations",
    )


class SourceResponse(BaseModel):
    """A source/citation in the research results."""

    url: str = Field(
        ...,
        description="Source URL",
    )
    title: str = Field(
        default="",
        description="Source title",
    )
    description: str = Field(
        default="",
        description="Description of information from source",
    )
    accessed_at: datetime = Field(
        ...,
        description="When the source was accessed",
    )

    @classmethod
    def from_source(cls, source: Source) -> "SourceResponse":
        """Create from internal Source model."""
        return cls(
            url=source.url,
            title=source.title,
            description=source.description,
            accessed_at=source.accessed_at,
        )


class ResearchStepResponse(BaseModel):
    """A single research step in the results."""

    step_id: str = Field(
        ...,
        description="Unique step identifier",
    )
    iteration: int = Field(
        ...,
        description="Iteration number",
    )
    question: str = Field(
        ...,
        description="Question researched in this step",
    )
    findings: str = Field(
        ...,
        description="Research findings",
    )
    confidence: float = Field(
        ...,
        description="Confidence score (0.0-1.0)",
    )
    sources: list[SourceResponse] = Field(
        default_factory=list,
        description="Sources used in this step",
    )
    timestamp: datetime = Field(
        ...,
        description="When this step completed",
    )


class ResearchResultResponse(BaseModel):
    """Complete research result response."""

    workflow_id: str = Field(
        ...,
        description="Workflow identifier",
    )
    query: str = Field(
        ...,
        description="Original research query",
    )
    status: ResearchStatus = Field(
        ...,
        description="Final research status",
    )
    final_summary: str = Field(
        ...,
        description="Comprehensive summary of findings",
    )
    total_iterations: int = Field(
        ...,
        description="Total iterations performed",
    )
    duration_seconds: float = Field(
        ...,
        description="Total execution duration in seconds",
    )
    steps: list[ResearchStepResponse] = Field(
        default_factory=list,
        description="All research steps performed",
    )
    sources: list[SourceResponse] = Field(
        default_factory=list,
        description="All unique sources cited",
    )
    started_at: datetime = Field(
        ...,
        description="When research started",
    )
    completed_at: datetime | None = Field(
        None,
        description="When research completed",
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(
        ...,
        description="Error type",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details",
    )
