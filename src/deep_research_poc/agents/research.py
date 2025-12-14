"""Research agent for conducting deep research.

This module implements the ResearchAgent that analyzes research questions,
uses tools to gather information, and synthesizes findings into structured outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from deep_research_poc.agents.base import BaseSpecializedAgent
from deep_research_poc.agents.tools import (
    calculate,
    fetch_url,
    get_current_datetime,
    web_search,
    wikipedia_search,
)
from deep_research_poc.config import Settings, get_settings
from deep_research_poc.models import ResearchStep

logger = structlog.get_logger()


@dataclass
class ResearchContext:
    """Context passed to research tools.
    
    Contains state and dependencies needed during research execution.
    """
    
    iteration: int
    previous_findings: list[str]
    original_query: str


class ResearchAgent(BaseSpecializedAgent[ResearchStep]):
    """AI-powered research agent using pydantic-ai and OpenAI.
    
    This agent orchestrates research by:
    1. Analyzing research questions
    2. Using tools to gather information
    3. Synthesizing findings into structured outputs
    
    Attributes:
        agent: The pydantic-ai agent for research tasks
        synthesis_agent: The pydantic-ai agent for synthesis tasks
        settings: Application settings
    """

    def __init__(
        self,
        agent: Any,
        synthesis_agent: Any | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the research agent.
        
        Args:
            agent: Pydantic-ai agent for research tasks
            synthesis_agent: Pydantic-ai agent for synthesis tasks
            settings: Optional settings (uses defaults if not provided)
        """
        super().__init__(agent, settings, "research_agent")
        self.synthesis_agent = synthesis_agent

    async def execute(
        self,
        question: str,
        iteration: int = 1,
        context: str = "",
    ) -> ResearchStep:
        """Execute research on a given question.

        Uses the AI agent with tools to investigate the question and
        produce structured findings.

        Args:
            question: The research question to investigate
            iteration: The current iteration number
            context: Additional context from previous research steps

        Returns:
            ResearchStep containing structured research findings
        """
        return await self.research(question, iteration, context)

    async def research(
        self,
        question: str,
        iteration: int,
        context: str = "",
    ) -> ResearchStep:
        """Conduct research on a given question.

        Uses the AI agent with tools to investigate the question and
        produce structured findings.

        Args:
            question: The research question to investigate
            iteration: The current iteration number
            context: Additional context from previous research steps

        Returns:
            ResearchStep containing structured research findings
            
        Raises:
            Exception: Propagated from agent if critical failure occurs
        """
        log = self._log_start(
            question=question[:100],
            iteration=iteration,
            has_context=bool(context),
        )

        prompt = self._build_research_prompt(question, iteration, context)

        try:
            result = await self.agent.run(prompt, message_history=None)
            research_step = result.output
            
            # Ensure iteration and question are set correctly
            research_step.iteration = iteration
            research_step.question = question

            self._log_success(
                log,
                confidence=research_step.confidence,
                requires_followup=research_step.requires_followup,
                num_sources=len(research_step.sources),
                num_followups=len(research_step.followup_questions),
            )

            return research_step

        except Exception as e:
            self._log_error(log, e)
            # Return a failed research step rather than crashing
            return ResearchStep(
                iteration=iteration,
                question=question,
                findings=f"Research failed: {str(e)}",
                confidence=0.0,
                sources=[],
                requires_followup=False,
                followup_questions=[],
            )

    def _build_research_prompt(
        self,
        question: str,
        iteration: int,
        context: str,
    ) -> str:
        """Build the research prompt for the AI agent.
        
        Args:
            question: The research question
            iteration: Current iteration number
            context: Previous context
            
        Returns:
            Formatted prompt string
        """
        parts = [
            f"Research Question: {question}",
            f"Iteration: {iteration}",
        ]
        
        if context:
            parts.append(f"Previous Context:\n{context}")
            
        parts.append(
            "\nPlease conduct thorough research using the available tools. "
            "Search for current information and cite your sources."
        )
        
        return "\n\n".join(parts)

    async def synthesize_findings(
        self,
        steps: list[ResearchStep],
        original_query: str,
    ) -> str:
        """Synthesize multiple research steps into a comprehensive summary.

        Combines findings from all research iterations into a coherent,
        well-structured summary that directly answers the original query.

        Args:
            steps: List of research steps to synthesize
            original_query: The original research query

        Returns:
            Comprehensive summary of all findings
        """
        log = logger.bind(
            original_query=original_query[:100],
            num_steps=len(steps),
        )
        log.info("synthesizing_findings")

        if not steps:
            return "No research steps to synthesize."

        if not self.synthesis_agent:
            return self._fallback_synthesis(steps, original_query)

        synthesis_prompt = self._build_synthesis_prompt(steps, original_query)

        try:
            result = await self.synthesis_agent.run(
                synthesis_prompt,
                message_history=None,
            )
            summary = result.output
            
            log.info("synthesis_completed", summary_length=len(summary))
            return summary

        except Exception as e:
            log.error("synthesis_failed", error=str(e), exc_info=True)
            # Fallback: basic concatenation of findings
            return self._fallback_synthesis(steps, original_query)

    def _build_synthesis_prompt(
        self,
        steps: list[ResearchStep],
        original_query: str,
    ) -> str:
        """Build the synthesis prompt.
        
        Args:
            steps: Research steps to synthesize
            original_query: Original query
            
        Returns:
            Formatted synthesis prompt
        """
        # Collect all unique sources for citation
        all_sources: list[tuple[str, str, str]] = []  # (url, title, description)
        seen_urls: set[str] = set()
        
        for step in steps:
            for source in step.sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    all_sources.append((source.url, source.title, source.description))
        
        # Format sources for reference
        sources_text = "\n".join(
            f"[{i+1}] {title or 'Untitled'} - {url}"
            for i, (url, title, _) in enumerate(all_sources)
        ) if all_sources else "No sources available"
        
        findings_text = "\n\n".join(
            f"## Step {step.iteration}\n"
            f"**Question:** {step.question}\n"
            f"**Findings:** {step.findings}\n"
            f"**Confidence:** {step.confidence:.0%}\n"
            f"**Sources:** {', '.join(str(s) for s in step.sources) if step.sources else 'None cited'}"
            for step in steps
        )

        return f"""# Research Synthesis Task

## Original Query
{original_query}

## Research Steps
{findings_text}

## All Sources (for citation)
{sources_text}

## Instructions
Synthesize the above research into a comprehensive, well-structured summary that:
1. Directly answers the original research query
2. Integrates insights from all research steps
3. Highlights key findings and patterns
4. Notes any limitations or areas of uncertainty
5. Provides actionable conclusions
6. References sources using [1], [2], etc. notation

Write a professional summary (3-5 paragraphs). End with a "## Sources" section listing referenced sources."""

    def _fallback_synthesis(
        self,
        steps: list[ResearchStep],
        original_query: str,
    ) -> str:
        """Create a basic synthesis when AI synthesis fails.
        
        Args:
            steps: Research steps
            original_query: Original query
            
        Returns:
            Basic concatenated summary with sources
        """
        findings = [
            f"**Finding {i+1}** (Confidence: {step.confidence:.0%}):\n{step.findings}"
            for i, step in enumerate(steps)
        ]
        
        # Collect all unique sources
        all_sources: list[str] = []
        seen_urls: set[str] = set()
        for step in steps:
            for source in step.sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    all_sources.append(f"- {source.title or 'Untitled'}: {source.url}")
        
        sources_section = "\n\n## Sources\n" + "\n".join(all_sources) if all_sources else ""
        
        return f"# Research Summary: {original_query}\n\n" + "\n\n---\n\n".join(findings) + sources_section


def create_research_agent(settings: Settings | None = None) -> ResearchAgent:
    """Factory function to create a ResearchAgent.
    
    Uses dependency injection for testability. The settings parameter
    allows for custom configuration in tests.
    
    Args:
        settings: Optional settings (uses defaults if not provided)
    
    Returns:
        Configured ResearchAgent instance
    """
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider
    
    settings = settings or get_settings()
    
    # Create the OpenAI model with explicit provider
    model = OpenAIChatModel(
        settings.openai_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )

    # Create research agent with structured output type
    research_agent: Agent[None, ResearchStep] = Agent(
        model,
        output_type=ResearchStep,
        system_prompt=_get_research_system_prompt(),
    )
    
    # Register tools
    research_agent.tool_plain(web_search)
    research_agent.tool_plain(fetch_url)
    research_agent.tool_plain(wikipedia_search)
    research_agent.tool_plain(calculate)
    research_agent.tool_plain(get_current_datetime)
    
    # Create synthesis agent for string output
    synthesis_agent: Agent[None, str] = Agent(
        model,
        output_type=str,
        system_prompt=_get_synthesis_system_prompt(),
    )
    
    logger.info(
        "research_agent_created",
        model=settings.openai_model,
        tools=["web_search", "fetch_url", "wikipedia_search", "calculate", "get_current_datetime"],
    )
    
    return ResearchAgent(
        agent=research_agent,
        synthesis_agent=synthesis_agent,
        settings=settings,
    )


def _get_research_system_prompt() -> str:
    """Get the system prompt for the research agent."""
    return """You are an expert research assistant conducting deep, thorough research.

## Your Responsibilities
1. Analyze research questions carefully
2. Break down complex topics into components
3. Use available tools to gather real, current information
4. Provide comprehensive findings with FULL CITATIONS
5. Assess confidence based on source quality
6. Identify when follow-up research would be valuable

## Available Tools
- `web_search(query, num_results)`: Search the web for current information
- `wikipedia_search(topic)`: Get Wikipedia summaries for background context
- `fetch_url(url)`: Fetch content from a specific URL
- `calculate(expression)`: Perform mathematical calculations
- `get_current_datetime()`: Get current date and time

## CRITICAL: Source Citation Requirements
You MUST populate the `sources` field with detailed citations:
- For EVERY piece of information from web searches, include the source
- Each source must have: url (required), title (the article/page title), description (what info you used)
- Format sources as a list of Source objects: [{"url": "...", "title": "...", "description": "..."}]
- Wikipedia sources should include the Wikipedia URL
- Web search results should include the actual source URLs, not just search URLs

## Guidelines
- ALWAYS use tools for factual queries - do not rely on training data alone
- Reference sources by number in your findings (e.g., "According to [1]...")
- Assign confidence scores honestly (0.0-1.0) based on evidence quality
- Set requires_followup=True if the topic needs deeper investigation
- Provide specific followup_questions when further research would help

## Output Format
Structure your output as a ResearchStep with all required fields, especially:
- findings: Your research results with source references
- sources: List of Source objects with url, title, and description for each source used
- confidence: Based on source reliability and coverage"""


def _get_synthesis_system_prompt() -> str:
    """Get the system prompt for the synthesis agent."""
    return """You are a research synthesizer creating comprehensive summaries with proper citations.

Your task is to combine multiple research findings into a coherent, well-structured summary.

Guidelines:
- Directly answer the original research question
- Integrate insights from all research steps
- Highlight key findings and patterns
- Include source references in your summary using [1], [2], etc. notation
- Note limitations and areas of uncertainty
- Provide actionable conclusions
- Use clear, professional language
- Structure with paragraphs and bullet points as appropriate

IMPORTANT: When referencing facts or claims, cite the sources provided in the research steps.
End your summary with a "Sources" section that lists all referenced sources."""
