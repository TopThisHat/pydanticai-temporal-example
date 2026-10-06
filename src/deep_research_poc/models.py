"""Core data models for deep research workflows.

This module defines Pydantic models for type-safe data structures used throughout
the research workflow system. Models follow best practices:
- Immutable by default (frozen=True) where appropriate
- Strict validation with Field constraints
- Clear documentation and examples
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


def utcnow() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


class ResearchStatus(str, Enum):
    """Status of a research task.
    
    States follow a linear progression for automated research:
    PENDING -> IN_PROGRESS -> COMPLETED | FAILED
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentEventType(str, Enum):
    """Type of agent event for UI display."""

    SYSTEM = "system"  # System messages (workflow start/end)
    AGENT_START = "agent_start"  # Agent beginning work
    AGENT_THINKING = "agent_thinking"  # Agent processing
    AGENT_RESULT = "agent_result"  # Agent completed with result
    AGENT_ERROR = "agent_error"  # Agent encountered error
    VALIDATION = "validation"  # Validation result
    CRITIQUE = "critique"  # Critique result


class AgentEvent(BaseModel):
    """An event from an agent during the research workflow.

    Used to display real-time progress in a chat-like interface.
    """

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this event",
    )
    timestamp: datetime = Field(
        default_factory=utcnow,
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
        description="Additional event details (agent-specific data)",
    )
    phase: str = Field(
        default="",
        description="Current workflow phase when event occurred",
    )


class Source(BaseModel):
    """A citation source with metadata.
    
    Represents a source used in research findings, including
    the URL, title, and a brief description of the content.
    """

    url: str = Field(
        ...,
        description="The URL of the source",
    )
    title: str = Field(
        default="",
        description="Title of the source (article, page, etc.)",
    )
    description: str = Field(
        default="",
        description="Brief description of what information was used from this source",
    )
    accessed_at: datetime = Field(
        default_factory=utcnow,
        description="When this source was accessed",
    )

    def __str__(self) -> str:
        """Return a formatted citation string."""
        if self.title:
            return f"{self.title} ({self.url})"
        return self.url


class ResearchQuery(BaseModel):
    """Input model for a research request.
    
    Represents the initial query that drives the research workflow.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The research question or topic to investigate",
    )
    max_iterations: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description=(
            "Maximum number of research iterations. "
            "Defaults to the value implied by 'depth' when not set."
        ),
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

    @model_validator(mode="after")
    def adjust_iterations_by_depth(self) -> "ResearchQuery":
        """Fill in max_iterations from depth when the caller did not set it.

        An explicit value is always respected, including 3.
        """
        depth_defaults = {"quick": 1, "standard": 3, "deep": 5}
        if self.max_iterations is None:
            object.__setattr__(self, "max_iterations", depth_defaults[self.depth])
        return self

    @property
    def iterations(self) -> int:
        """max_iterations after validation, typed as the int it always is."""
        assert self.max_iterations is not None
        return self.max_iterations


class ResearchStep(BaseModel):
    """Individual research step in the workflow.
    
    Represents a single iteration of research with findings, confidence,
    and optional follow-up questions for deeper investigation.
    """

    step_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this step",
    )
    iteration: int = Field(
        ...,
        ge=1,
        description="Iteration number in the research process",
    )
    question: str = Field(
        ...,
        description="Specific question being researched in this step",
    )
    findings: str = Field(
        ...,
        description="Research findings for this step",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of findings (0.0 = low, 1.0 = high)",
    )
    sources: list[Source] = Field(
        default_factory=list,
        description="Sources with citations used in research (URLs, titles, descriptions)",
    )
    timestamp: datetime = Field(
        default_factory=utcnow,
        description="When this step completed",
    )
    requires_followup: bool = Field(
        default=False,
        description="Whether this step requires additional research",
    )
    followup_questions: list[str] = Field(
        default_factory=list,
        description="Follow-up questions for deeper investigation",
    )

    def get_citation_list(self) -> list[str]:
        """Return a list of formatted citations."""
        return [str(source) for source in self.sources]


class ResearchResult(BaseModel):
    """Final result of the research workflow.
    
    Aggregates all research steps and provides a comprehensive summary
    of the research conducted.
    """

    query: str = Field(
        ...,
        description="Original research query",
    )
    status: ResearchStatus = Field(
        ...,
        description="Final status of the research",
    )
    steps: list[ResearchStep] = Field(
        default_factory=list,
        description="All research steps performed",
    )
    final_summary: str = Field(
        default="",
        description="Comprehensive summary synthesizing all findings",
    )
    total_iterations: int = Field(
        default=0,
        ge=0,
        description="Total iterations performed",
    )
    started_at: datetime = Field(
        ...,
        description="When research started",
    )
    completed_at: datetime | None = Field(
        None,
        description="When research completed",
    )
    error_message: str | None = Field(
        None,
        description="Error message if research failed",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds if completed."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def all_sources(self) -> list[Source]:
        """Aggregate all unique sources from all research steps."""
        seen_urls: set[str] = set()
        unique_sources: list[Source] = []
        for step in self.steps:
            for source in step.sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    unique_sources.append(source)
        return unique_sources

    def get_formatted_citations(self) -> str:
        """Return a formatted string of all citations."""
        sources = self.all_sources
        if not sources:
            return "No sources cited."
        
        citations: list[str] = []
        for i, source in enumerate(sources, 1):
            citation = f"[{i}] {source.title or 'Untitled'}"
            if source.description:
                citation += f"\n    {source.description}"
            citation += f"\n    URL: {source.url}"
            citations.append(citation)
        
        return "\n\n".join(citations)


class WorkflowInput(BaseModel):
    """Input for the Temporal research workflow.
    
    Encapsulates all inputs needed to start a research workflow.
    """

    research_query: ResearchQuery = Field(
        ...,
        description="The research query to process",
    )
    workflow_id: str = Field(
        default_factory=lambda: f"research-{uuid4()}",
        description="Unique workflow identifier",
    )


class WorkflowOutput(BaseModel):
    """Output from the Temporal research workflow.
    
    Contains the complete research result along with workflow metadata.
    """

    result: ResearchResult = Field(
        ...,
        description="The complete research result",
    )
    workflow_id: str = Field(
        ...,
        description="The workflow ID that produced this result",
    )
    duration_seconds: float = Field(
        ...,
        ge=0.0,
        description="Total workflow execution duration in seconds",
    )


# =============================================================================
# Multi-Agent Architecture Models
# =============================================================================


class ResearchSubTask(BaseModel):
    """A sub-task in the research plan.
    
    Represents a single research task that needs to be completed
    as part of the overall research plan.
    """

    task_id: str = Field(
        ...,
        description="Unique identifier for this sub-task",
    )
    description: str = Field(
        ...,
        description="What needs to be researched",
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Priority level (1=highest, 5=lowest)",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Task IDs that must be completed before this task",
    )
    estimated_complexity: str = Field(
        default="medium",
        pattern="^(simple|medium|complex)$",
        description="Estimated complexity of the task",
    )
    search_queries: list[str] = Field(
        default_factory=list,
        description="Suggested search queries for this task",
    )
    is_completed: bool = Field(
        default=False,
        description="Whether this sub-task has been completed",
    )
    findings: str = Field(
        default="",
        description="Findings for this sub-task once completed",
    )


class ResearchPlan(BaseModel):
    """A structured research plan created by the PlanningAgent.
    
    Breaks down a complex query into manageable sub-tasks with
    dependencies and priorities.
    """

    plan_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this plan",
    )
    original_query: str = Field(
        ...,
        description="The original research query",
    )
    query_analysis: str = Field(
        ...,
        description="Analysis of what the query is asking for",
    )
    key_entities: list[str] = Field(
        default_factory=list,
        description="Key entities identified in the query",
    )
    sub_tasks: list[ResearchSubTask] = Field(
        ...,
        min_length=1,
        description="List of research sub-tasks to complete",
    )
    expected_output_format: str = Field(
        default="comprehensive report",
        description="Expected format of the final output",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="When this plan was created",
    )

    def get_pending_tasks(self) -> list[ResearchSubTask]:
        """Get all pending (not completed) tasks."""
        return [task for task in self.sub_tasks if not task.is_completed]

    def get_ready_tasks(self) -> list[ResearchSubTask]:
        """Get tasks that are ready to execute (dependencies met)."""
        completed_ids = {t.task_id for t in self.sub_tasks if t.is_completed}
        return [
            task for task in self.sub_tasks
            if not task.is_completed
            and all(dep in completed_ids for dep in task.dependencies)
        ]

    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.sub_tasks:
            return 0.0
        completed = sum(1 for t in self.sub_tasks if t.is_completed)
        return completed / len(self.sub_tasks) * 100


class ValidationIssue(BaseModel):
    """An issue found during validation.
    
    Represents a gap, inconsistency, or missing element in the research.
    """

    issue_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
        description="Unique identifier for this issue",
    )
    issue_type: str = Field(
        ...,
        pattern="^(missing_answer|incomplete_answer|inconsistency|unsupported_claim|missing_source)$",
        description="Type of validation issue",
    )
    severity: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical)$",
        description="Severity of the issue",
    )
    description: str = Field(
        ...,
        description="Description of the issue",
    )
    related_query_part: str = Field(
        default="",
        description="Part of the original query this issue relates to",
    )
    suggested_action: str = Field(
        default="",
        description="Suggested action to resolve this issue",
    )
    is_resolved: bool = Field(
        default=False,
        description="Whether this issue has been resolved",
    )


class ValidationResult(BaseModel):
    """Result of validation by the ValidationAgent.
    
    Contains whether the research is complete and any issues found.
    """

    validation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this validation",
    )
    is_valid: bool = Field(
        ...,
        description="Whether the research fully answers the query",
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How complete the answer is (0.0-1.0)",
    )
    accuracy_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated accuracy of the answer (0.0-1.0)",
    )
    coverage_analysis: str = Field(
        ...,
        description="Analysis of how well the query is covered",
    )
    issues: list[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues found",
    )
    unanswered_parts: list[str] = Field(
        default_factory=list,
        description="Parts of the query that remain unanswered",
    )
    additional_queries: list[str] = Field(
        default_factory=list,
        description="Specific search queries to fill gaps in research",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for improving the research",
    )
    validated_at: datetime = Field(
        default_factory=utcnow,
        description="When validation was performed",
    )

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(issue.severity == "critical" for issue in self.issues)

    def get_unresolved_issues(self) -> list[ValidationIssue]:
        """Get all unresolved issues."""
        return [issue for issue in self.issues if not issue.is_resolved]


class CritiqueResult(BaseModel):
    """Result of critique by the CritiqueAgent.
    
    Provides detailed feedback on research quality and suggestions
    for improvement.
    """

    critique_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this critique",
    )
    overall_quality: str = Field(
        ...,
        pattern="^(poor|fair|good|excellent)$",
        description="Overall quality assessment",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Numerical quality score (0.0-1.0)",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Strengths of the research",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Weaknesses of the research",
    )
    source_quality_assessment: str = Field(
        default="",
        description="Assessment of source quality and reliability",
    )
    factual_concerns: list[str] = Field(
        default_factory=list,
        description="Potential factual concerns or claims to verify",
    )
    improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="Specific suggestions for improvement",
    )
    additional_queries: list[str] = Field(
        default_factory=list,
        description="Additional queries that could improve the research",
    )
    requires_revision: bool = Field(
        default=False,
        description="Whether revision is recommended",
    )
    critiqued_at: datetime = Field(
        default_factory=utcnow,
        description="When critique was performed",
    )


class ExpandedQuery(BaseModel):
    """Result of query expansion by QueryExpansionAgent.
    
    Contains the expanded and refined version of the original query.
    """

    expansion_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this expansion",
    )
    original_query: str = Field(
        ...,
        description="The original query",
    )
    interpreted_intent: str = Field(
        ...,
        description="The interpreted intent behind the query",
    )
    clarifying_questions: list[str] = Field(
        default_factory=list,
        description="Questions that could help clarify the query",
    )
    expanded_queries: list[str] = Field(
        ...,
        min_length=1,
        description="Expanded/refined versions of the query",
    )
    related_topics: list[str] = Field(
        default_factory=list,
        description="Related topics that might be relevant",
    )
    search_terms: list[str] = Field(
        default_factory=list,
        description="Recommended search terms",
    )
    scope_definition: str = Field(
        default="",
        description="Definition of the scope for the research",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="When this expansion was created",
    )


class AgentHandoff(BaseModel):
    """Represents a handoff between agents in the multi-agent workflow.
    
    Tracks the flow of work between different specialized agents.
    """

    handoff_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this handoff",
    )
    from_agent: str = Field(
        ...,
        description="Agent that is handing off",
    )
    to_agent: str = Field(
        ...,
        description="Agent that is receiving",
    )
    context: str = Field(
        ...,
        description="Context being passed",
    )
    instructions: str = Field(
        default="",
        description="Specific instructions for the receiving agent",
    )
    priority: str = Field(
        default="normal",
        pattern="^(low|normal|high|urgent)$",
        description="Priority of this handoff",
    )
    timestamp: datetime = Field(
        default_factory=utcnow,
        description="When this handoff occurred",
    )


class MultiAgentWorkflowState(BaseModel):
    """State tracking for multi-agent workflows.
    
    Maintains the state of a research workflow across multiple agents.
    """

    workflow_id: str = Field(
        ...,
        description="Unique workflow identifier",
    )
    current_agent: str = Field(
        default="planner",
        description="Currently active agent",
    )
    research_plan: ResearchPlan | None = Field(
        default=None,
        description="The research plan if created",
    )
    research_steps: list[ResearchStep] = Field(
        default_factory=list,
        description="Completed research steps",
    )
    validation_results: list[ValidationResult] = Field(
        default_factory=list,
        description="Validation results from each iteration",
    )
    critique_results: list[CritiqueResult] = Field(
        default_factory=list,
        description="Critique results from each iteration",
    )
    handoffs: list[AgentHandoff] = Field(
        default_factory=list,
        description="History of agent handoffs",
    )
    iteration_count: int = Field(
        default=0,
        description="Number of research-validate-critique iterations",
    )
    is_complete: bool = Field(
        default=False,
        description="Whether the workflow is complete",
    )
    final_summary: str = Field(
        default="",
        description="Final synthesized summary",
    )
    started_at: datetime = Field(
        default_factory=utcnow,
        description="When workflow started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When workflow completed",
    )
