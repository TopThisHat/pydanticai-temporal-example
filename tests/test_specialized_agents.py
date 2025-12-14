"""Tests for specialized agents.

This module tests the PlanningAgent, ValidationAgent, CritiqueAgent,
and QueryExpansionAgent implementations.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deep_research_poc.models import (
    CritiqueResult,
    ExpandedQuery,
    ResearchPlan,
    ResearchStep,
    ResearchSubTask,
    Source,
    ValidationIssue,
    ValidationResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_research_step() -> ResearchStep:
    """Create a sample research step for testing."""
    return ResearchStep(
        iteration=1,
        question="What is quantum computing?",
        findings="Quantum computing uses quantum mechanics to perform computations.",
        confidence=0.85,
        sources=[
            Source(
                url="https://example.com/quantum",
                title="Introduction to Quantum Computing",
                description="Overview of quantum computing basics",
            )
        ],
        requires_followup=False,
        followup_questions=[],
    )


@pytest.fixture
def sample_research_plan() -> ResearchPlan:
    """Create a sample research plan for testing."""
    return ResearchPlan(
        original_query="What are the impacts of climate change?",
        query_analysis="Query asks about climate change impacts across multiple domains",
        key_entities=["climate change", "impacts", "environment"],
        sub_tasks=[
            ResearchSubTask(
                task_id="task-1",
                description="Research environmental impacts",
                priority=1,
                search_queries=["climate change environmental impacts 2024"],
            ),
            ResearchSubTask(
                task_id="task-2",
                description="Research economic impacts",
                priority=2,
                dependencies=["task-1"],
                search_queries=["climate change economic costs"],
            ),
        ],
    )


@pytest.fixture
def sample_validation_result() -> ValidationResult:
    """Create a sample validation result for testing."""
    return ValidationResult(
        is_valid=True,
        completeness_score=0.9,
        accuracy_score=0.85,
        coverage_analysis="All major aspects of the query are addressed",
        issues=[],
        unanswered_parts=[],
        recommendations=["Consider adding more recent data"],
    )


@pytest.fixture
def sample_critique_result() -> CritiqueResult:
    """Create a sample critique result for testing."""
    return CritiqueResult(
        overall_quality="good",
        quality_score=0.8,
        strengths=["Well-sourced", "Comprehensive coverage"],
        weaknesses=["Could use more recent data"],
        source_quality_assessment="Sources are authoritative and relevant",
        improvement_suggestions=["Add more recent statistics"],
        requires_revision=False,
    )


@pytest.fixture
def sample_expanded_query() -> ExpandedQuery:
    """Create a sample expanded query for testing."""
    return ExpandedQuery(
        original_query="What is AI?",
        interpreted_intent="User wants to understand artificial intelligence basics",
        expanded_queries=[
            "What is artificial intelligence and how does it work?",
            "Types of AI and machine learning",
            "AI applications and use cases",
        ],
        related_topics=["machine learning", "deep learning", "neural networks"],
        search_terms=["artificial intelligence", "AI basics", "machine learning"],
    )


# =============================================================================
# PlanningAgent Tests
# =============================================================================


class TestPlanningAgent:
    """Tests for the PlanningAgent."""

    @pytest.mark.asyncio
    async def test_execute_creates_plan(
        self,
        sample_research_plan: ResearchPlan,
    ) -> None:
        """Test that execute creates a research plan."""
        from deep_research_poc.agents.planning import PlanningAgent

        # Mock the pydantic-ai agent
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = sample_research_plan
        mock_agent.run = AsyncMock(return_value=mock_result)

        agent = PlanningAgent(agent=mock_agent)

        result = await agent.execute(
            query="What are the impacts of climate change?",
            context="",
        )

        assert isinstance(result, ResearchPlan)
        assert len(result.sub_tasks) == 2
        assert result.key_entities == ["climate change", "impacts", "environment"]
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_error(self) -> None:
        """Test that execute returns fallback plan on error."""
        from deep_research_poc.agents.planning import PlanningAgent

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=Exception("API Error"))

        agent = PlanningAgent(agent=mock_agent)

        result = await agent.execute(
            query="Test query",
            context="",
        )

        assert isinstance(result, ResearchPlan)
        assert len(result.sub_tasks) == 1  # Fallback creates single task
        assert "fallback" in result.sub_tasks[0].task_id

    def test_build_prompt_includes_query(self) -> None:
        """Test that _build_prompt includes the query."""
        from deep_research_poc.agents.planning import PlanningAgent

        mock_agent = MagicMock()
        agent = PlanningAgent(agent=mock_agent)

        prompt = agent._build_prompt("Test query", "")

        assert "Test query" in prompt
        assert "Research Query" in prompt

    def test_build_prompt_includes_context(self) -> None:
        """Test that _build_prompt includes context when provided."""
        from deep_research_poc.agents.planning import PlanningAgent

        mock_agent = MagicMock()
        agent = PlanningAgent(agent=mock_agent)

        prompt = agent._build_prompt("Test query", "Some context")

        assert "Some context" in prompt
        assert "Additional Context" in prompt


# =============================================================================
# ValidationAgent Tests
# =============================================================================


class TestValidationAgent:
    """Tests for the ValidationAgent."""

    @pytest.mark.asyncio
    async def test_execute_validates_research(
        self,
        sample_research_step: ResearchStep,
        sample_validation_result: ValidationResult,
    ) -> None:
        """Test that execute validates research findings."""
        from deep_research_poc.agents.validation import ValidationAgent

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = sample_validation_result
        mock_agent.run = AsyncMock(return_value=mock_result)

        agent = ValidationAgent(agent=mock_agent)

        result = await agent.execute(
            original_query="What is quantum computing?",
            research_steps=[sample_research_step],
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.completeness_score == 0.9
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_error(
        self,
        sample_research_step: ResearchStep,
    ) -> None:
        """Test that execute returns fallback on error."""
        from deep_research_poc.agents.validation import ValidationAgent

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=Exception("API Error"))

        agent = ValidationAgent(agent=mock_agent)

        result = await agent.execute(
            original_query="Test query",
            research_steps=[sample_research_step],
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert len(result.issues) > 0

    def test_build_prompt_includes_findings(
        self,
        sample_research_step: ResearchStep,
    ) -> None:
        """Test that _build_prompt includes research findings."""
        from deep_research_poc.agents.validation import ValidationAgent

        mock_agent = MagicMock()
        agent = ValidationAgent(agent=mock_agent)

        prompt = agent._build_prompt(
            query="Test query",
            steps=[sample_research_step],
            plan=None,
            summary="",
        )

        assert "Step 1" in prompt
        assert "quantum mechanics" in prompt


# =============================================================================
# CritiqueAgent Tests
# =============================================================================


class TestCritiqueAgent:
    """Tests for the CritiqueAgent."""

    @pytest.mark.asyncio
    async def test_execute_critiques_research(
        self,
        sample_research_step: ResearchStep,
        sample_critique_result: CritiqueResult,
    ) -> None:
        """Test that execute provides critique of research."""
        from deep_research_poc.agents.critique import CritiqueAgent

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = sample_critique_result
        mock_agent.run = AsyncMock(return_value=mock_result)

        agent = CritiqueAgent(agent=mock_agent)

        result = await agent.execute(
            original_query="What is quantum computing?",
            research_steps=[sample_research_step],
            current_summary="Summary of findings",
        )

        assert isinstance(result, CritiqueResult)
        assert result.overall_quality == "good"
        assert result.quality_score == 0.8
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_error(
        self,
        sample_research_step: ResearchStep,
    ) -> None:
        """Test that execute returns fallback on error."""
        from deep_research_poc.agents.critique import CritiqueAgent

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=Exception("API Error"))

        agent = CritiqueAgent(agent=mock_agent)

        result = await agent.execute(
            original_query="Test query",
            research_steps=[sample_research_step],
            current_summary="Summary",
        )

        assert isinstance(result, CritiqueResult)
        assert result.requires_revision is True


# =============================================================================
# QueryExpansionAgent Tests
# =============================================================================


class TestQueryExpansionAgent:
    """Tests for the QueryExpansionAgent."""

    @pytest.mark.asyncio
    async def test_execute_expands_query(
        self,
        sample_expanded_query: ExpandedQuery,
    ) -> None:
        """Test that execute expands a query."""
        from deep_research_poc.agents.query_expansion import QueryExpansionAgent

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = sample_expanded_query
        mock_agent.run = AsyncMock(return_value=mock_result)

        agent = QueryExpansionAgent(agent=mock_agent)

        result = await agent.execute(
            query="What is AI?",
        )

        assert isinstance(result, ExpandedQuery)
        assert len(result.expanded_queries) == 3
        assert len(result.search_terms) > 0
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_error(self) -> None:
        """Test that execute returns fallback on error."""
        from deep_research_poc.agents.query_expansion import QueryExpansionAgent

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=Exception("API Error"))

        agent = QueryExpansionAgent(agent=mock_agent)

        result = await agent.execute(query="Test query")

        assert isinstance(result, ExpandedQuery)
        assert result.original_query == "Test query"
        assert len(result.expanded_queries) == 1  # Fallback has original query

    def test_build_prompt_includes_failed_searches(self) -> None:
        """Test that _build_prompt includes failed searches."""
        from deep_research_poc.agents.query_expansion import QueryExpansionAgent

        mock_agent = MagicMock()
        agent = QueryExpansionAgent(agent=mock_agent)

        prompt = agent._build_prompt(
            query="Test query",
            context="",
            failed_searches=["failed search 1", "failed search 2"],
        )

        assert "failed search 1" in prompt
        assert "Previously Failed Searches" in prompt


# =============================================================================
# Model Tests
# =============================================================================


class TestResearchPlanModel:
    """Tests for the ResearchPlan model."""

    def test_get_pending_tasks(self, sample_research_plan: ResearchPlan) -> None:
        """Test get_pending_tasks returns incomplete tasks."""
        pending = sample_research_plan.get_pending_tasks()
        assert len(pending) == 2

        # Mark one as complete
        sample_research_plan.sub_tasks[0].is_completed = True
        pending = sample_research_plan.get_pending_tasks()
        assert len(pending) == 1

    def test_get_ready_tasks(self, sample_research_plan: ResearchPlan) -> None:
        """Test get_ready_tasks returns tasks with met dependencies."""
        ready = sample_research_plan.get_ready_tasks()
        # Only task-1 is ready (task-2 depends on task-1)
        assert len(ready) == 1
        assert ready[0].task_id == "task-1"

        # Mark task-1 as complete
        sample_research_plan.sub_tasks[0].is_completed = True
        ready = sample_research_plan.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "task-2"

    def test_completion_percentage(self, sample_research_plan: ResearchPlan) -> None:
        """Test completion_percentage calculation."""
        assert sample_research_plan.completion_percentage() == 0.0

        sample_research_plan.sub_tasks[0].is_completed = True
        assert sample_research_plan.completion_percentage() == 50.0

        sample_research_plan.sub_tasks[1].is_completed = True
        assert sample_research_plan.completion_percentage() == 100.0


class TestValidationResultModel:
    """Tests for the ValidationResult model."""

    def test_has_critical_issues(self) -> None:
        """Test has_critical_issues detection."""
        result = ValidationResult(
            is_valid=False,
            completeness_score=0.5,
            accuracy_score=0.5,
            coverage_analysis="Partial coverage",
            issues=[
                ValidationIssue(
                    issue_type="missing_answer",
                    severity="medium",
                    description="Missing some info",
                )
            ],
        )
        assert result.has_critical_issues() is False

        result.issues.append(
            ValidationIssue(
                issue_type="missing_answer",
                severity="critical",
                description="Critical missing info",
            )
        )
        assert result.has_critical_issues() is True

    def test_get_unresolved_issues(self) -> None:
        """Test get_unresolved_issues filtering."""
        result = ValidationResult(
            is_valid=False,
            completeness_score=0.5,
            accuracy_score=0.5,
            coverage_analysis="Partial coverage",
            issues=[
                ValidationIssue(
                    issue_type="missing_answer",
                    severity="high",
                    description="Issue 1",
                    is_resolved=True,
                ),
                ValidationIssue(
                    issue_type="incomplete_answer",
                    severity="medium",
                    description="Issue 2",
                    is_resolved=False,
                ),
            ],
        )
        unresolved = result.get_unresolved_issues()
        assert len(unresolved) == 1
        assert unresolved[0].description == "Issue 2"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestAgentFactories:
    """Tests for agent factory functions."""

    @patch("deep_research_poc.agents.planning.Agent")
    @patch("deep_research_poc.agents.planning.OpenAIChatModel")
    @patch("deep_research_poc.agents.planning.OpenAIProvider")
    def test_create_planning_agent(
        self,
        mock_provider: MagicMock,
        mock_model: MagicMock,
        mock_agent_class: MagicMock,
    ) -> None:
        """Test create_planning_agent factory."""
        from deep_research_poc.agents.planning import create_planning_agent
        from deep_research_poc.config import Settings

        settings = Settings(
            openai_api_key="test-key",
            openai_model="gpt-4",
        )

        agent = create_planning_agent(settings)

        from deep_research_poc.agents.planning import PlanningAgent
        assert isinstance(agent, PlanningAgent)
        mock_agent_class.assert_called_once()

    @patch("deep_research_poc.agents.validation.Agent")
    @patch("deep_research_poc.agents.validation.OpenAIChatModel")
    @patch("deep_research_poc.agents.validation.OpenAIProvider")
    def test_create_validation_agent(
        self,
        mock_provider: MagicMock,
        mock_model: MagicMock,
        mock_agent_class: MagicMock,
    ) -> None:
        """Test create_validation_agent factory."""
        from deep_research_poc.agents.validation import create_validation_agent
        from deep_research_poc.config import Settings

        settings = Settings(
            openai_api_key="test-key",
            openai_model="gpt-4",
        )

        agent = create_validation_agent(settings)

        from deep_research_poc.agents.validation import ValidationAgent
        assert isinstance(agent, ValidationAgent)

    @patch("deep_research_poc.agents.critique.Agent")
    @patch("deep_research_poc.agents.critique.OpenAIChatModel")
    @patch("deep_research_poc.agents.critique.OpenAIProvider")
    def test_create_critique_agent(
        self,
        mock_provider: MagicMock,
        mock_model: MagicMock,
        mock_agent_class: MagicMock,
    ) -> None:
        """Test create_critique_agent factory."""
        from deep_research_poc.agents.critique import create_critique_agent
        from deep_research_poc.config import Settings

        settings = Settings(
            openai_api_key="test-key",
            openai_model="gpt-4",
        )

        agent = create_critique_agent(settings)

        from deep_research_poc.agents.critique import CritiqueAgent
        assert isinstance(agent, CritiqueAgent)

    @patch("deep_research_poc.agents.query_expansion.Agent")
    @patch("deep_research_poc.agents.query_expansion.OpenAIChatModel")
    @patch("deep_research_poc.agents.query_expansion.OpenAIProvider")
    def test_create_query_expansion_agent(
        self,
        mock_provider: MagicMock,
        mock_model: MagicMock,
        mock_agent_class: MagicMock,
    ) -> None:
        """Test create_query_expansion_agent factory."""
        from deep_research_poc.agents.query_expansion import create_query_expansion_agent
        from deep_research_poc.config import Settings

        settings = Settings(
            openai_api_key="test-key",
            openai_model="gpt-4",
        )

        agent = create_query_expansion_agent(settings)

        from deep_research_poc.agents.query_expansion import QueryExpansionAgent
        assert isinstance(agent, QueryExpansionAgent)
