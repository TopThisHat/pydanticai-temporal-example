"""Validation agent for research completeness verification.

This module implements the ValidationAgent that checks if research findings
fully answer all parts of the original query and identifies gaps.
"""

from __future__ import annotations

from typing import Any

import structlog

from deep_research_poc.agents.base import BaseSpecializedAgent
from deep_research_poc.config import Settings, get_settings
from deep_research_poc.models import (
    ResearchPlan,
    ResearchStep,
    ValidationIssue,
    ValidationResult,
)

logger = structlog.get_logger()


class ValidationAgent(BaseSpecializedAgent[ValidationResult]):
    """Agent that validates research completeness and accuracy.
    
    The ValidationAgent examines research findings against the original
    query and plan to determine:
    - Whether all parts of the query are answered
    - Completeness score for the research
    - Any gaps or missing information
    - Issues that need to be addressed
    
    Attributes:
        agent: The pydantic-ai agent for validation
        settings: Application settings
    """

    def __init__(
        self,
        agent: Any,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the validation agent.
        
        Args:
            agent: Pydantic-ai agent for validation tasks
            settings: Optional settings (uses defaults if not provided)
        """
        super().__init__(agent, settings, "validation_agent")

    async def execute(
        self,
        original_query: str,
        research_steps: list[ResearchStep],
        research_plan: ResearchPlan | None = None,
        current_summary: str = "",
    ) -> ValidationResult:
        """Validate research findings against the original query.
        
        Examines all research steps and determines if the query
        is fully answered with proper sourcing.
        
        Args:
            original_query: The original research query
            research_steps: All completed research steps
            research_plan: Optional research plan to check against
            current_summary: Optional current synthesis
            
        Returns:
            ValidationResult with completeness assessment
        """
        log = self._log_start(
            query=original_query[:100],
            num_steps=len(research_steps),
            has_plan=research_plan is not None,
        )

        prompt = self._build_prompt(
            original_query,
            research_steps,
            research_plan,
            current_summary,
        )

        try:
            result = await self.agent.run(prompt, message_history=None)
            validation: ValidationResult = result.output

            self._log_success(
                log,
                is_valid=validation.is_valid,
                completeness=validation.completeness_score,
                num_issues=len(validation.issues),
            )
            return validation

        except Exception as e:
            self._log_error(log, e)
            # Return a validation indicating review is needed
            return self._create_fallback_validation(str(e))

    def _build_prompt(
        self,
        query: str,
        steps: list[ResearchStep],
        plan: ResearchPlan | None,
        summary: str,
    ) -> str:
        """Build the validation prompt.
        
        Args:
            query: Original query
            steps: Research steps to validate
            plan: Optional research plan
            summary: Current synthesis
            
        Returns:
            Formatted prompt string
        """
        parts = [
            f"## Original Research Query\n{query}",
        ]
        
        if plan:
            tasks_text = "\n".join(
                f"- [{task.task_id}] {task.description} "
                f"(priority: {task.priority}, completed: {task.is_completed})"
                for task in plan.sub_tasks
            )
            parts.append(f"## Research Plan Tasks\n{tasks_text}")
        
        # Format research findings
        if steps:
            findings_text = "\n\n".join(
                f"### Step {step.iteration}: {step.question}\n"
                f"**Findings:** {step.findings[:1000]}...\n"
                f"**Confidence:** {step.confidence:.0%}\n"
                f"**Sources:** {len(step.sources)} cited"
                for step in steps
            )
            parts.append(f"## Research Findings\n{findings_text}")
        else:
            parts.append("## Research Findings\nNo research has been conducted yet.")
        
        if summary:
            parts.append(f"## Current Summary\n{summary[:2000]}")
        
        parts.append(
            "\n## Validation Task\n"
            "Carefully analyze whether the research findings fully answer the original query. "
            "Check for completeness, accuracy of sourcing, and identify any gaps."
        )
        
        return "\n\n".join(parts)

    def _create_fallback_validation(self, error: str) -> ValidationResult:
        """Create a fallback validation when the agent fails.
        
        Args:
            error: Error message
            
        Returns:
            ValidationResult indicating manual review needed
        """
        return ValidationResult(
            is_valid=False,
            completeness_score=0.0,
            accuracy_score=0.0,
            coverage_analysis=f"Validation failed: {error}. Manual review recommended.",
            issues=[
                ValidationIssue(
                    issue_type="missing_answer",
                    severity="high",
                    description="Automated validation failed. Please review manually.",
                    suggested_action="Retry validation or review findings manually.",
                )
            ],
            recommendations=["Retry validation process", "Review research findings manually"],
        )


def create_validation_agent(settings: Settings | None = None) -> ValidationAgent:
    """Factory function to create a ValidationAgent.
    
    Uses dependency injection for testability.
    
    Args:
        settings: Optional settings (uses defaults if not provided)
        
    Returns:
        Configured ValidationAgent instance
    """
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    settings = settings or get_settings()

    model = OpenAIChatModel(
        settings.openai_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )

    validation_agent: Agent[None, ValidationResult] = Agent(
        model,
        output_type=ValidationResult,
        system_prompt=_get_validation_system_prompt(),
    )

    logger.info(
        "validation_agent_created",
        model=settings.openai_model,
    )

    return ValidationAgent(agent=validation_agent, settings=settings)


def _get_validation_system_prompt() -> str:
    """Get the system prompt for the validation agent."""
    return """You are a research validation expert. Your job is to critically evaluate 
whether research findings fully and accurately answer the original query, and generate
specific search queries to fill any gaps.

## Your Responsibilities
1. Parse the original query to identify ALL questions/components being asked
2. Check if EACH component has been addressed in the findings
3. Evaluate the quality and reliability of sources used
4. Identify any gaps, inconsistencies, or unsupported claims
5. Provide a completeness score based on coverage
6. Flag any issues that need to be addressed
7. Generate specific search queries to fill identified gaps

## Validation Criteria

### Completeness Check
- Has every part of the query been addressed?
- Are there sub-questions that remain unanswered?
- Is there sufficient depth on each topic?

### Source Quality Check
- Are claims supported by cited sources?
- Are sources reliable and appropriate?
- Are there any unsupported assertions?

### Accuracy Check
- Are there any contradictions in the findings?
- Do the conclusions follow from the evidence?
- Are there potential factual errors?

## Issue Types
- missing_answer: A part of the query is not addressed at all
- incomplete_answer: A topic is mentioned but not fully covered
- inconsistency: Contradictory information in findings
- unsupported_claim: Claims without proper source citation
- missing_source: Key facts lacking source attribution

## Severity Levels
- critical: Cannot deliver a valid answer without addressing
- high: Significantly impacts answer quality
- medium: Noticeable gap but answer is still useful
- low: Minor improvement opportunity

## Scoring Guidelines
- completeness_score: 0.0-1.0 based on % of query components answered
  - 1.0 = Every part fully addressed with depth
  - 0.7 = Most parts addressed, some gaps
  - 0.5 = About half the query answered
  - 0.3 = Major portions missing
  - 0.0 = Query not meaningfully addressed

- accuracy_score: 0.0-1.0 based on source quality and consistency
  - 1.0 = All claims sourced, no inconsistencies
  - 0.7 = Most claims sourced, minor issues
  - 0.5 = Some unsourced claims or inconsistencies
  - 0.3 = Significant sourcing problems
  - 0.0 = Major accuracy concerns

## is_valid Criteria
Set is_valid=True ONLY if:
- completeness_score >= 0.8
- accuracy_score >= 0.7
- No critical issues
- No more than 2 high-severity issues

## Additional Queries (CRITICAL)
When the research is incomplete (is_valid=False), you MUST provide specific search 
queries in the `additional_queries` field. These should be targeted searches to:
- Answer any unanswered parts of the original query
- Fill gaps identified in the completeness check
- Address any missing_answer or incomplete_answer issues
- Provide more depth where needed

For each gap identified, create a focused, searchable query that would help fill that gap.
Make queries specific and actionable (e.g., "Python asyncio vs threading performance benchmarks 2024" 
rather than "learn more about Python").

Be thorough and specific in your validation. Provide actionable feedback."""
