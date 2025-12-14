"""Critique agent for research quality assessment.

This module implements the CritiqueAgent that provides detailed
feedback on research quality and suggests improvements.
"""

from __future__ import annotations

from typing import Any

import structlog

from deep_research_poc.agents.base import BaseSpecializedAgent
from deep_research_poc.config import Settings, get_settings
from deep_research_poc.models import CritiqueResult, ResearchStep, Source, ValidationResult

logger = structlog.get_logger()


class CritiqueAgent(BaseSpecializedAgent[CritiqueResult]):
    """Agent that critiques research quality and suggests improvements.
    
    The CritiqueAgent provides in-depth analysis of research including:
    - Strengths and weaknesses assessment
    - Source quality evaluation
    - Factual concern identification
    - Specific improvement suggestions
    - Additional research queries
    
    Attributes:
        agent: The pydantic-ai agent for critique
        settings: Application settings
    """

    def __init__(
        self,
        agent: Any,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the critique agent.
        
        Args:
            agent: Pydantic-ai agent for critique tasks
            settings: Optional settings (uses defaults if not provided)
        """
        super().__init__(agent, settings, "critique_agent")

    async def execute(
        self,
        original_query: str,
        research_steps: list[ResearchStep],
        current_summary: str,
        validation_result: ValidationResult | None = None,
    ) -> CritiqueResult:
        """Critique research findings and provide improvement suggestions.
        
        Analyzes the research quality and provides actionable feedback
        for improving the final output.
        
        Args:
            original_query: The original research query
            research_steps: All completed research steps
            current_summary: Current synthesized summary
            validation_result: Optional validation result to consider
            
        Returns:
            CritiqueResult with quality assessment and suggestions
        """
        log = self._log_start(
            query=original_query[:100],
            num_steps=len(research_steps),
            has_validation=validation_result is not None,
        )

        prompt = self._build_prompt(
            original_query,
            research_steps,
            current_summary,
            validation_result,
        )

        try:
            result = await self.agent.run(prompt, message_history=None)
            critique: CritiqueResult = result.output

            self._log_success(
                log,
                quality=critique.overall_quality,
                score=critique.quality_score,
                requires_revision=critique.requires_revision,
            )
            return critique

        except Exception as e:
            self._log_error(log, e)
            return self._create_fallback_critique(str(e))

    def _build_prompt(
        self,
        query: str,
        steps: list[ResearchStep],
        summary: str,
        validation: ValidationResult | None,
    ) -> str:
        """Build the critique prompt.
        
        Args:
            query: Original query
            steps: Research steps
            summary: Current synthesis
            validation: Optional validation result
            
        Returns:
            Formatted prompt string
        """
        parts: list[str] = [
            f"## Original Research Query\n{query}",
        ]
        
        # Add research findings summary
        if steps:
            findings_summary: list[str] = []
            all_sources: list[Source] = []
            for step in steps:
                findings_summary.append(
                    f"**Step {step.iteration}** (confidence: {step.confidence:.0%}):\n"
                    f"{step.findings[:800]}"
                )
                all_sources.extend(step.sources)
            
            parts.append(f"## Research Findings\n" + "\n\n---\n".join(findings_summary))
            
            # Add source summary
            if all_sources:
                source_list = "\n".join(
                    f"- {s.title or 'Untitled'}: {s.url}"
                    for s in all_sources[:10]  # Limit to first 10
                )
                parts.append(f"## Sources Used (first 10)\n{source_list}")
        
        parts.append(f"## Current Summary\n{summary[:3000]}")
        
        if validation:
            parts.append(
                f"## Validation Result\n"
                f"- Valid: {validation.is_valid}\n"
                f"- Completeness: {validation.completeness_score:.0%}\n"
                f"- Accuracy: {validation.accuracy_score:.0%}\n"
                f"- Issues: {len(validation.issues)}"
            )
        
        parts.append(
            "\n## Critique Task\n"
            "Provide a thorough critique of this research. Evaluate quality, "
            "identify strengths and weaknesses, assess sources, and suggest "
            "specific improvements. Recommend additional queries if needed."
        )
        
        return "\n\n".join(parts)

    def _create_fallback_critique(self, error: str) -> CritiqueResult:
        """Create a fallback critique when the agent fails.
        
        Args:
            error: Error message
            
        Returns:
            CritiqueResult indicating manual review needed
        """
        return CritiqueResult(
            overall_quality="fair",
            quality_score=0.5,
            strengths=["Research was conducted"],
            weaknesses=[f"Automated critique failed: {error}"],
            source_quality_assessment="Unable to assess - critique process failed",
            improvement_suggestions=["Retry critique process", "Manual review recommended"],
            requires_revision=True,
        )


def create_critique_agent(settings: Settings | None = None) -> CritiqueAgent:
    """Factory function to create a CritiqueAgent.
    
    Uses dependency injection for testability.
    
    Args:
        settings: Optional settings (uses defaults if not provided)
        
    Returns:
        Configured CritiqueAgent instance
    """
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    settings = settings or get_settings()

    model = OpenAIChatModel(
        settings.openai_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )

    critique_agent: Agent[None, CritiqueResult] = Agent(
        model,
        output_type=CritiqueResult,
        system_prompt=_get_critique_system_prompt(),
    )

    logger.info(
        "critique_agent_created",
        model=settings.openai_model,
    )

    return CritiqueAgent(agent=critique_agent, settings=settings)


def _get_critique_system_prompt() -> str:
    """Get the system prompt for the critique agent."""
    return """You are a research quality expert and critical evaluator. Your job is to 
provide constructive, actionable feedback on research quality.

## Your Responsibilities
1. Evaluate overall research quality objectively
2. Identify specific strengths that should be preserved
3. Pinpoint weaknesses that need improvement
4. Assess the quality and reliability of sources
5. Flag potential factual concerns or claims to verify
6. Provide specific, actionable improvement suggestions
7. Suggest additional queries for gaps in coverage

## Quality Assessment Framework

### Overall Quality Levels
- excellent: Comprehensive, well-sourced, directly answers query (0.85-1.0)
- good: Thorough with minor gaps, mostly well-sourced (0.70-0.84)
- fair: Adequate but notable gaps or sourcing issues (0.50-0.69)
- poor: Major gaps, poor sourcing, or fails to answer query (0.0-0.49)

### Strength Categories
- Comprehensive coverage of topic
- High-quality, authoritative sources
- Well-structured and clear presentation
- Balanced perspectives included
- Current/up-to-date information
- Proper citation and attribution

### Weakness Categories
- Missing key aspects of the query
- Weak or unreliable sources
- Unsupported claims or assertions
- Outdated information
- Bias or one-sided coverage
- Poor organization or clarity
- Factual errors or inconsistencies

### Source Quality Criteria
- Authority: Is the source authoritative on this topic?
- Currency: Is the information current?
- Reliability: Is this a reliable source type?
- Diversity: Are multiple perspectives represented?
- Depth: Do sources provide sufficient detail?

## Improvement Suggestions Guidelines
- Be SPECIFIC - don't say "improve sourcing", say "find authoritative sources for claim X"
- Be ACTIONABLE - suggestions should be implementable
- Prioritize - focus on highest-impact improvements first
- Be CONSTRUCTIVE - frame as opportunities, not just criticisms

## Additional Query Suggestions
When suggesting additional queries:
- Address specific gaps identified
- Use search-optimized phrasing
- Focus on missing entities or concepts
- Target authoritative source types when appropriate

## requires_revision Criteria
Set requires_revision=True if:
- quality_score < 0.7
- Any factual concerns are identified
- Major gaps in query coverage
- Significant sourcing problems

Be thorough but fair. Good research deserves recognition; poor research needs specific guidance."""
