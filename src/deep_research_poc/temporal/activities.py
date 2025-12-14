"""Temporal activities for research workflows.

Activities are the building blocks of Temporal workflows. They encapsulate
the actual work to be done and can be retried independently.

Design principles:
- Each activity is idempotent where possible
- Activities handle their own logging
- Errors are propagated for workflow-level retry decisions
"""

from __future__ import annotations

import structlog
from temporalio import activity

from deep_research_poc.agents.research import create_research_agent
from deep_research_poc.models import (
    ExpandedQuery,
    ResearchPlan,
    ResearchStep,
    ValidationResult,
)

logger = structlog.get_logger()


@activity.defn
async def conduct_research_activity(
    question: str,
    iteration: int,
    context: str = "",
) -> ResearchStep:
    """Conduct research on a question using the AI agent.

    This activity wraps the research agent to make it retriable
    and observable within the Temporal workflow.

    Args:
        question: The research question to investigate
        iteration: Current iteration number (1-indexed)
        context: Context from previous research steps

    Returns:
        ResearchStep with structured findings

    Raises:
        Exception: Propagated from agent for workflow retry handling
    """
    log = logger.bind(
        activity="conduct_research",
        question=question[:100],
        iteration=iteration,
    )
    log.info("activity_started")
    
    try:
        agent = create_research_agent()
        result = await agent.research(
            question=question,
            iteration=iteration,
            context=context,
        )
        
        log.info(
            "activity_completed",
            confidence=result.confidence,
            requires_followup=result.requires_followup,
            num_sources=len(result.sources),
        )
        
        return result
        
    except Exception as e:
        log.error("activity_failed", error=str(e), exc_info=True)
        raise


@activity.defn
async def synthesize_findings_activity(
    steps: list[ResearchStep],
    original_query: str,
) -> str:
    """Synthesize multiple research steps into a final summary.

    Combines findings from all research iterations into a coherent
    summary that directly addresses the original query.

    Args:
        steps: All completed research steps
        original_query: The original research query

    Returns:
        Comprehensive summary string

    Raises:
        Exception: Propagated from agent for workflow retry handling
    """
    log = logger.bind(
        activity="synthesize_findings",
        num_steps=len(steps),
        original_query=original_query[:100],
    )
    log.info("activity_started")
    
    try:
        agent = create_research_agent()
        summary = await agent.synthesize_findings(
            steps=steps,
            original_query=original_query,
        )
        
        log.info("activity_completed", summary_length=len(summary))
        return summary
        
    except Exception as e:
        log.error("activity_failed", error=str(e), exc_info=True)
        raise


# =============================================================================
# Multi-Agent Activities
# =============================================================================


@activity.defn
async def create_research_plan_activity(
    query: str,
    context: str = "",
) -> ResearchPlan:
    """Create a research plan for a query using the PlanningAgent.

    Breaks down a complex query into manageable sub-tasks with
    dependencies and priorities.

    Args:
        query: The research query to plan for
        context: Optional additional context

    Returns:
        ResearchPlan with structured sub-tasks

    Raises:
        Exception: Propagated from agent for workflow retry handling
    """
    from deep_research_poc.agents.planning import create_planning_agent

    log = logger.bind(
        activity="create_research_plan",
        query=query[:100],
    )
    log.info("activity_started")

    try:
        agent = create_planning_agent()
        plan = await agent.execute(query=query, context=context)

        log.info(
            "activity_completed",
            num_tasks=len(plan.sub_tasks),
            num_entities=len(plan.key_entities),
        )
        return plan

    except Exception as e:
        log.error("activity_failed", error=str(e), exc_info=True)
        raise


@activity.defn
async def validate_research_activity(
    original_query: str,
    research_steps: list[ResearchStep],
    research_plan: ResearchPlan | None = None,
    current_summary: str = "",
) -> ValidationResult:
    """Validate research findings against the original query.

    Uses the ValidationAgent to check if all parts of the query
    are answered with proper sourcing.

    Args:
        original_query: The original research query
        research_steps: All completed research steps
        research_plan: Optional research plan to check against
        current_summary: Optional current synthesis

    Returns:
        ValidationResult with completeness assessment

    Raises:
        Exception: Propagated from agent for workflow retry handling
    """
    from deep_research_poc.agents.validation import create_validation_agent

    log = logger.bind(
        activity="validate_research",
        query=original_query[:100],
        num_steps=len(research_steps),
    )
    log.info("activity_started")

    try:
        agent = create_validation_agent()
        result = await agent.execute(
            original_query=original_query,
            research_steps=research_steps,
            research_plan=research_plan,
            current_summary=current_summary,
        )

        log.info(
            "activity_completed",
            is_valid=result.is_valid,
            completeness=result.completeness_score,
            num_issues=len(result.issues),
        )
        return result

    except Exception as e:
        log.error("activity_failed", error=str(e), exc_info=True)
        raise


@activity.defn
async def expand_query_activity(
    query: str,
    context: str = "",
    failed_searches: list[str] | None = None,
) -> ExpandedQuery:
    """Expand and refine a research query.

    Uses the QueryExpansionAgent to produce optimized query
    versions for better research coverage.

    Args:
        query: The original research query
        context: Optional additional context
        failed_searches: Previous search queries that didn't yield results

    Returns:
        ExpandedQuery with refined queries and search terms

    Raises:
        Exception: Propagated from agent for workflow retry handling
    """
    from deep_research_poc.agents.query_expansion import create_query_expansion_agent

    log = logger.bind(
        activity="expand_query",
        query=query[:100],
    )
    log.info("activity_started")

    try:
        agent = create_query_expansion_agent()
        result = await agent.execute(
            query=query,
            context=context,
            failed_searches=failed_searches,
        )

        log.info(
            "activity_completed",
            num_expanded=len(result.expanded_queries),
            num_search_terms=len(result.search_terms),
        )
        return result

    except Exception as e:
        log.error("activity_failed", error=str(e), exc_info=True)
        raise
