"""Planning agent for research task decomposition.

This module implements the PlanningAgent that analyzes research queries
and breaks them down into structured sub-tasks with dependencies and priorities.
"""

from __future__ import annotations

from typing import Any

import structlog

from deep_research_poc.agents.base import BaseSpecializedAgent
from deep_research_poc.config import Settings, get_settings
from deep_research_poc.models import ResearchPlan, ResearchSubTask

logger = structlog.get_logger()


class PlanningAgent(BaseSpecializedAgent[ResearchPlan]):
    """Agent that creates structured research plans.
    
    The PlanningAgent analyzes a research query and produces a
    structured plan with:
    - Analysis of the query's intent
    - Identification of key entities
    - Sub-tasks with dependencies and priorities
    - Suggested search queries for each sub-task
    
    Attributes:
        agent: The pydantic-ai agent for planning
        settings: Application settings
    """

    def __init__(
        self,
        agent: Any,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the planning agent.
        
        Args:
            agent: Pydantic-ai agent for planning tasks
            settings: Optional settings (uses defaults if not provided)
        """
        super().__init__(agent, settings, "planning_agent")

    async def execute(
        self,
        query: str,
        context: str = "",
    ) -> ResearchPlan:
        """Create a research plan for the given query.
        
        Analyzes the query and produces a structured plan with
        sub-tasks, dependencies, and priorities.
        
        Args:
            query: The research query to plan for
            context: Optional additional context
            
        Returns:
            ResearchPlan with structured sub-tasks
        """
        log = self._log_start(query=query[:100], has_context=bool(context))

        prompt = self._build_prompt(query, context)

        try:
            result = await self.agent.run(prompt, message_history=None)
            plan: ResearchPlan = result.output
            
            # Ensure original query is set
            if not plan.original_query:
                plan = plan.model_copy(update={"original_query": query})

            self._log_success(
                log,
                num_tasks=len(plan.sub_tasks),
                num_entities=len(plan.key_entities),
            )
            return plan

        except Exception as e:
            self._log_error(log, e)
            # Return a minimal fallback plan
            return self._create_fallback_plan(query, str(e))

    def _build_prompt(self, query: str, context: str) -> str:
        """Build the planning prompt.
        
        Args:
            query: Research query
            context: Additional context
            
        Returns:
            Formatted prompt string
        """
        parts = [
            f"## Research Query\n{query}",
        ]
        
        if context:
            parts.append(f"## Additional Context\n{context}")
            
        parts.append(
            "\n## Task\n"
            "Analyze this research query and create a comprehensive research plan. "
            "Break it down into manageable sub-tasks that can be researched independently."
        )
        
        return "\n\n".join(parts)

    def _create_fallback_plan(self, query: str, error: str) -> ResearchPlan:
        """Create a minimal fallback plan when planning fails.
        
        Args:
            query: Original query
            error: Error message
            
        Returns:
            Basic ResearchPlan
        """
        return ResearchPlan(
            original_query=query,
            query_analysis=f"Planning failed: {error}. Proceeding with basic research.",
            key_entities=[],
            sub_tasks=[
                ResearchSubTask(
                    task_id="fallback-1",
                    description=f"Research: {query}",
                    priority=1,
                    search_queries=[query],
                )
            ],
        )


def create_planning_agent(settings: Settings | None = None) -> PlanningAgent:
    """Factory function to create a PlanningAgent.
    
    Uses dependency injection for testability.
    
    Args:
        settings: Optional settings (uses defaults if not provided)
        
    Returns:
        Configured PlanningAgent instance
    """
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    settings = settings or get_settings()

    model = OpenAIChatModel(
        settings.openai_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )

    planning_agent: Agent[None, ResearchPlan] = Agent(
        model,
        output_type=ResearchPlan,
        system_prompt=_get_planning_system_prompt(),
    )

    logger.info(
        "planning_agent_created",
        model=settings.openai_model,
    )

    return PlanningAgent(agent=planning_agent, settings=settings)


def _get_planning_system_prompt() -> str:
    """Get the system prompt for the planning agent."""
    return """You are a research planning expert. Your job is to analyze research queries 
and create comprehensive, actionable research plans.

## Your Responsibilities
1. Understand the full scope of the research question
2. Identify all key entities, concepts, and relationships mentioned
3. Break down complex queries into atomic, researchable sub-tasks
4. Establish dependencies between tasks (what needs to be researched first)
5. Prioritize tasks based on importance and logical order
6. Suggest specific search queries for each sub-task

## Guidelines for Creating Sub-Tasks
- Each sub-task should be specific and focused on ONE aspect
- Tasks should be independent where possible
- Complex queries may need 5-10 sub-tasks; simple ones 2-3
- Include background/context gathering as early tasks
- Include verification/cross-referencing as later tasks

## Priority Levels
1 = Critical - Must be answered for any useful response
2 = High - Important for comprehensive answer
3 = Medium - Adds valuable detail
4 = Low - Nice to have
5 = Optional - Only if time permits

## Complexity Levels
- simple: Can be answered with a single search
- medium: Requires multiple searches and synthesis
- complex: Requires deep research, multiple sources, verification

## Output Format
Structure your response as a ResearchPlan with:
- query_analysis: Your analysis of what's being asked
- key_entities: Main entities/concepts identified
- sub_tasks: List of ResearchSubTask objects
- expected_output_format: What the final output should look like

## Example Query Analysis
For "What are the environmental and economic impacts of electric vehicles vs gasoline cars?"
- This asks about TWO types of impacts (environmental, economic)
- Comparing TWO vehicle types
- Sub-tasks might include: EV environmental impact, gas car environmental impact, 
  EV economic factors, gas car economic factors, comparison synthesis

Be thorough but practical. Create a plan that leads to a complete answer."""
