"""Tests for research agent."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from deep_research_poc.agents.research import ResearchAgent
from deep_research_poc.models import ResearchStep, Source


@pytest.mark.asyncio
async def test_research_agent_initialization() -> None:
    """Test that research agent initializes correctly."""
    mock_research_agent = MagicMock()
    mock_synthesis_agent = MagicMock()
    
    agent = ResearchAgent(agent=mock_research_agent, synthesis_agent=mock_synthesis_agent)
    assert agent is not None
    assert agent.agent is not None
    assert agent.synthesis_agent is not None


@pytest.mark.asyncio
async def test_conduct_research_success() -> None:
    """Test successful research execution."""
    mock_research_agent = MagicMock()
    mock_synthesis_agent = MagicMock()

    mock_result = MagicMock()
    mock_result.output = ResearchStep(
        iteration=1,
        question="What is Python?",
        findings="Python is a high-level programming language.",
        confidence=0.95,
        sources=[
            Source(url="https://python.org", title="Python.org", description="Official Python website"),
            Source(url="https://wikipedia.org/wiki/Python", title="Wikipedia", description="Python article"),
        ],
        requires_followup=False,
        followup_questions=[],
    )

    mock_research_agent.run = AsyncMock(return_value=mock_result)

    agent = ResearchAgent(agent=mock_research_agent, synthesis_agent=mock_synthesis_agent)

    result = await agent.research(
        question="What is Python?",
        iteration=1,
        context="",
    )

    assert result.iteration == 1
    assert result.question == "What is Python?"
    assert result.confidence == 0.95
    assert len(result.sources) == 2
    assert not result.requires_followup


@pytest.mark.asyncio
async def test_conduct_research_with_followup() -> None:
    """Test research that requires followup."""
    mock_research_agent = MagicMock()
    mock_synthesis_agent = MagicMock()

    mock_result = MagicMock()
    mock_result.output = ResearchStep(
        iteration=1,
        question="What is AI?",
        findings="AI is artificial intelligence.",
        confidence=0.7,
        sources=[Source(url="https://example.com/ai", title="AI Source", description="AI info")],
        requires_followup=True,
        followup_questions=["What are the types of AI?"],
    )

    mock_research_agent.run = AsyncMock(return_value=mock_result)

    agent = ResearchAgent(agent=mock_research_agent, synthesis_agent=mock_synthesis_agent)

    result = await agent.research(
        question="What is AI?",
        iteration=1,
        context="",
    )

    assert result.requires_followup
    assert len(result.followup_questions) == 1
    assert "types of AI" in result.followup_questions[0]


@pytest.mark.asyncio
async def test_research_handles_errors() -> None:
    """Test that research handles errors gracefully."""
    mock_research_agent = MagicMock()
    mock_synthesis_agent = MagicMock()

    mock_research_agent.run = AsyncMock(side_effect=Exception("API Error"))

    agent = ResearchAgent(agent=mock_research_agent, synthesis_agent=mock_synthesis_agent)

    result = await agent.research(
        question="Test question",
        iteration=1,
        context="",
    )

    assert result.confidence == 0.0
    assert "failed" in result.findings.lower()
    assert not result.requires_followup


@pytest.mark.asyncio
async def test_synthesize_findings() -> None:
    """Test synthesizing multiple research steps."""
    mock_research_agent = MagicMock()
    mock_synthesis_agent = MagicMock()

    mock_result = MagicMock()
    mock_result.output = "Comprehensive summary of all findings."
    mock_synthesis_agent.run = AsyncMock(return_value=mock_result)

    agent = ResearchAgent(agent=mock_research_agent, synthesis_agent=mock_synthesis_agent)

    steps = [
        ResearchStep(
            iteration=1,
            question="What is Python?",
            findings="Python is a programming language.",
            confidence=0.9,
            sources=[Source(url="https://python.org", title="Python.org", description="Official site")],
        ),
        ResearchStep(
            iteration=2,
            question="What are Python features?",
            findings="Python has many features.",
            confidence=0.85,
            sources=[Source(url="https://docs.python.org", title="Python Docs", description="Documentation")],
        ),
    ]

    summary = await agent.synthesize_findings(
        steps=steps,
        original_query="Tell me about Python",
    )

    assert isinstance(summary, str)
    assert len(summary) > 0


@pytest.mark.asyncio
async def test_synthesize_findings_error_fallback() -> None:
    """Test synthesis fallback on error."""
    mock_research_agent = MagicMock()
    mock_synthesis_agent = MagicMock()

    mock_synthesis_agent.run = AsyncMock(side_effect=Exception("Synthesis error"))

    agent = ResearchAgent(agent=mock_research_agent, synthesis_agent=mock_synthesis_agent)

    steps = [
        ResearchStep(
            iteration=1,
            question="Test",
            findings="Test findings",
            confidence=0.8,
            sources=[],
        ),
    ]

    summary = await agent.synthesize_findings(
        steps=steps,
        original_query="Test query",
    )

    # Should return fallback summary
    assert "Test query" in summary
    assert "Test findings" in summary


@pytest.mark.asyncio
async def test_synthesize_empty_steps() -> None:
    """Test synthesis with empty steps list."""
    mock_research_agent = MagicMock()
    mock_synthesis_agent = MagicMock()

    agent = ResearchAgent(agent=mock_research_agent, synthesis_agent=mock_synthesis_agent)

    summary = await agent.synthesize_findings(
        steps=[],
        original_query="Test query",
    )

    assert "No research steps" in summary
