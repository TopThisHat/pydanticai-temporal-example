"""Query expansion agent for refining research queries.

This module implements the QueryExpansionAgent that analyzes queries
and produces expanded, refined versions for better research results.
"""

from __future__ import annotations

from typing import Any

import structlog

from deep_research_poc.agents.base import BaseSpecializedAgent
from deep_research_poc.config import Settings, get_settings
from deep_research_poc.models import ExpandedQuery

logger = structlog.get_logger()


class QueryExpansionAgent(BaseSpecializedAgent[ExpandedQuery]):
    """Agent that expands and refines research queries.
    
    The QueryExpansionAgent analyzes a query and produces:
    - Interpreted intent of the query
    - Clarifying questions for ambiguity
    - Expanded/refined query versions
    - Related topics to explore
    - Optimized search terms
    
    Attributes:
        agent: The pydantic-ai agent for expansion
        settings: Application settings
    """

    def __init__(
        self,
        agent: Any,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the query expansion agent.
        
        Args:
            agent: Pydantic-ai agent for expansion tasks
            settings: Optional settings (uses defaults if not provided)
        """
        super().__init__(agent, settings, "query_expansion_agent")

    async def execute(
        self,
        query: str,
        context: str = "",
        failed_searches: list[str] | None = None,
    ) -> ExpandedQuery:
        """Expand and refine a research query.
        
        Analyzes the query and produces optimized versions
        for better research coverage.
        
        Args:
            query: The original research query
            context: Optional additional context
            failed_searches: Previous search queries that didn't yield results
            
        Returns:
            ExpandedQuery with refined queries and search terms
        """
        log = self._log_start(
            query=query[:100],
            has_context=bool(context),
            num_failed=len(failed_searches) if failed_searches else 0,
        )

        prompt = self._build_prompt(query, context, failed_searches or [])

        try:
            result = await self.agent.run(prompt, message_history=None)
            expansion: ExpandedQuery = result.output
            
            # Ensure original query is set
            if not expansion.original_query:
                expansion = expansion.model_copy(update={"original_query": query})

            self._log_success(
                log,
                num_expanded=len(expansion.expanded_queries),
                num_search_terms=len(expansion.search_terms),
            )
            return expansion

        except Exception as e:
            self._log_error(log, e)
            return self._create_fallback_expansion(query, str(e))

    def _build_prompt(
        self,
        query: str,
        context: str,
        failed_searches: list[str],
    ) -> str:
        """Build the expansion prompt.
        
        Args:
            query: Original query
            context: Additional context
            failed_searches: Previously failed searches
            
        Returns:
            Formatted prompt string
        """
        parts = [
            f"## Original Query\n{query}",
        ]
        
        if context:
            parts.append(f"## Additional Context\n{context}")
        
        if failed_searches:
            failed_text = "\n".join(f"- {s}" for s in failed_searches)
            parts.append(
                f"## Previously Failed Searches\n"
                f"These searches didn't yield useful results:\n{failed_text}"
            )
        
        parts.append(
            "\n## Task\n"
            "Analyze this query and create expanded, refined versions that will "
            "lead to more comprehensive research results. Consider synonyms, "
            "related concepts, and different phrasings."
        )
        
        return "\n\n".join(parts)

    def _create_fallback_expansion(self, query: str, error: str) -> ExpandedQuery:
        """Create a fallback expansion when the agent fails.
        
        Args:
            query: Original query
            error: Error message
            
        Returns:
            Basic ExpandedQuery
        """
        return ExpandedQuery(
            original_query=query,
            interpreted_intent=f"Unable to interpret: {error}",
            expanded_queries=[query],
            search_terms=[query],
        )


def create_query_expansion_agent(settings: Settings | None = None) -> QueryExpansionAgent:
    """Factory function to create a QueryExpansionAgent.
    
    Uses dependency injection for testability.
    
    Args:
        settings: Optional settings (uses defaults if not provided)
        
    Returns:
        Configured QueryExpansionAgent instance
    """
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    settings = settings or get_settings()

    model = OpenAIChatModel(
        settings.openai_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )

    expansion_agent: Agent[None, ExpandedQuery] = Agent(
        model,
        output_type=ExpandedQuery,
        system_prompt=_get_expansion_system_prompt(),
    )

    logger.info(
        "query_expansion_agent_created",
        model=settings.openai_model,
    )

    return QueryExpansionAgent(agent=expansion_agent, settings=settings)


def _get_expansion_system_prompt() -> str:
    """Get the system prompt for the query expansion agent."""
    return """You are a search query optimization expert. Your job is to analyze 
research queries and expand them for comprehensive information retrieval.

## Your Responsibilities
1. Understand the true intent behind the query
2. Identify ambiguities that might affect research
3. Create expanded, refined query versions
4. Identify related topics that enrich understanding
5. Generate optimized search terms

## Query Analysis Process

### Intent Interpretation
- What is the user really trying to learn?
- What type of answer are they expecting? (factual, comparative, explanatory)
- What's the scope? (specific fact, broad overview, deep dive)
- Is there implicit context or assumptions?

### Clarifying Questions
- What ambiguities exist in the query?
- What assumptions might the user be making?
- What clarifications would most improve research?

### Query Expansion Strategies
1. **Synonym expansion**: Use alternative terms for key concepts
2. **Specificity adjustment**: Create more specific and more general versions
3. **Aspect decomposition**: Break into component questions
4. **Temporal framing**: Add time context if relevant
5. **Entity expansion**: Include related entities or alternatives
6. **Perspective diversification**: Consider different viewpoints

### Search Term Optimization
- Use quotes for exact phrases when needed
- Include synonyms and abbreviations
- Add qualifying terms (latest, official, research)
- Consider domain-specific terminology
- Include relevant entity names

## Output Guidelines

### expanded_queries
- Provide 3-5 refined versions of the query
- Each should capture a different aspect or approach
- Make them search-engine optimized
- Vary specificity levels

### related_topics
- What adjacent topics would enrich understanding?
- What background knowledge helps?
- What related entities are relevant?

### search_terms
- Optimized individual search terms
- Include key entities, concepts, synonyms
- Mix of general and specific terms
- Domain-specific terminology

### scope_definition
- Define clear boundaries for the research
- What's included and excluded?
- What depth is appropriate?

Be thorough but focused. The goal is to maximize research coverage and quality."""
