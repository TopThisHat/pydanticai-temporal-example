"""Temporal workflows for deep research.

This module implements the multi-agent research workflow using Temporal for
durable execution. The workflow orchestrates multiple specialized agents for
comprehensive research with planning and validation loops.

Design principles:
- Deterministic workflow code (uses workflow.* APIs)
- Activities for non-deterministic operations
- Multi-agent orchestration for comprehensive research
- Validation loops to ensure all user questions are answered
- Comprehensive logging for observability
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from deep_research_poc.models import (
    AgentEvent,
    AgentEventType,
    ExpandedQuery,
    ResearchPlan,
    ResearchResult,
    ResearchStatus,
    ResearchStep,
    ValidationResult,
    WorkflowInput,
    WorkflowOutput,
)

# Import activities with proper passthrough for Temporal sandbox
with workflow.unsafe.imports_passed_through():
    from deep_research_poc.temporal.activities import (
        conduct_research_activity,
        create_research_plan_activity,
        expand_query_activity,
        synthesize_findings_activity,
        validate_research_activity,
    )


# Retry policies for different agent types
PLANNING_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)

RESEARCH_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)

VALIDATION_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=20),
    maximum_attempts=2,
    backoff_coefficient=2.0,
)

SYNTHESIS_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=2,
    backoff_coefficient=2.0,
)


@workflow.defn
class DeepResearchWorkflow:
    """Multi-agent workflow for comprehensive deep research.

    This workflow orchestrates multiple specialized agents:
    1. QueryExpansionAgent - Refines and expands the query
    2. PlanningAgent - Creates structured research plan
    3. ResearchAgent - Executes research tasks
    4. ValidationAgent - Validates completeness and identifies gaps for additional research
    5. SynthesisAgent - Combines findings

    The workflow includes feedback loops for iterative improvement
    when validation identifies unanswered parts of the query.
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        self._research_steps: list[ResearchStep] = []
        self._research_plan: ResearchPlan | None = None
        self._validation_results: list[ValidationResult] = []
        self._agent_events: list[AgentEvent] = []
        self._current_phase: str = "initializing"
        self._iteration_count: int = 0
        self._status: ResearchStatus = ResearchStatus.PENDING

    def _add_event(
        self,
        event_type: AgentEventType,
        agent_name: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add an agent event to the event log.

        Args:
            event_type: Type of event
            agent_name: Name of the agent
            message: Human-readable message
            details: Optional additional details
        """
        # Use workflow.uuid4() for deterministic UUID generation in workflow
        event = AgentEvent(
            event_id=workflow.uuid4(),
            timestamp=workflow.now(),
            event_type=event_type,
            agent_name=agent_name,
            message=message,
            details=details or {},
            phase=self._current_phase,
        )
        self._agent_events.append(event)

    @workflow.run
    async def run(self, input_data: WorkflowInput) -> WorkflowOutput:
        """Execute the multi-agent research workflow.

        Args:
            input_data: Workflow input containing research query and config

        Returns:
            WorkflowOutput with complete research results
        """
        start_time = workflow.now()
        query = input_data.research_query
        max_iterations = query.max_iterations

        workflow.logger.info(
            "multi_agent_workflow_started",
            extra={
                "workflow_id": input_data.workflow_id,
                "query": query.query[:100],
                "max_iterations": max_iterations,
                "depth": query.depth,
            },
        )

        self._status = ResearchStatus.IN_PROGRESS
        
        # Add initial system event
        self._add_event(
            AgentEventType.SYSTEM,
            "Workflow",
            f"🔬 Starting research: {query.query[:100]}{'...' if len(query.query) > 100 else ''}",
            {"max_iterations": max_iterations, "depth": query.depth},
        )

        result = ResearchResult(
            query=query.query,
            status=ResearchStatus.IN_PROGRESS,
            started_at=workflow.now(),
        )

        try:
            # Phase 1: Query Expansion
            self._current_phase = "query_expansion"
            self._add_event(
                AgentEventType.AGENT_START,
                "QueryExpansionAgent",
                "🔍 Analyzing and expanding your query for better research coverage...",
            )
            expanded_query = await self._expand_query(query.query)

            # Phase 2: Research Planning
            self._current_phase = "planning"
            self._add_event(
                AgentEventType.AGENT_START,
                "PlanningAgent",
                "📋 Creating a structured research plan with sub-tasks...",
            )
            self._research_plan = await self._create_plan(
                query.query,
                expanded_query,
            )

            # Phase 3: Execute Research with Validation Loop
            self._current_phase = "research"
            self._add_event(
                AgentEventType.AGENT_START,
                "ResearchAgent",
                f"🔎 Beginning research across {len(self._research_plan.sub_tasks)} planned tasks...",
                {"num_tasks": len(self._research_plan.sub_tasks)},
            )
            await self._execute_research_loop(
                original_query=query.query,
                max_iterations=max_iterations,
            )

            # Phase 4: Final Synthesis
            self._current_phase = "synthesis"
            self._add_event(
                AgentEventType.AGENT_START,
                "SynthesisAgent",
                "✨ Synthesizing all findings into a comprehensive summary...",
            )
            if self._research_steps:
                final_summary = await self._synthesize_with_quality_check(
                    original_query=query.query,
                )
                result.final_summary = final_summary

            result.steps = self._research_steps
            result.total_iterations = len(self._research_steps)
            result.status = ResearchStatus.COMPLETED
            self._status = ResearchStatus.COMPLETED
            self._current_phase = "completed"
            
            # Add completion event
            self._add_event(
                AgentEventType.SYSTEM,
                "Workflow",
                f"✅ Research completed! Found {len(result.all_sources)} sources across {result.total_iterations} research steps.",
                {
                    "total_iterations": result.total_iterations,
                    "num_sources": len(result.all_sources),
                },
            )

            workflow.logger.info(
                "multi_agent_workflow_completed",
                extra={
                    "status": result.status.value,
                    "total_iterations": result.total_iterations,
                    "validation_iterations": len(self._validation_results),
                },
            )

        except Exception as e:
            workflow.logger.error(
                "multi_agent_workflow_failed",
                extra={"error": str(e), "phase": self._current_phase},
            )
            # Add error event
            self._add_event(
                AgentEventType.AGENT_ERROR,
                "Workflow",
                f"❌ Research failed in phase '{self._current_phase}': {str(e)}",
                {"error": str(e), "phase": self._current_phase},
            )
            result.status = ResearchStatus.FAILED
            result.error_message = f"Failed in phase '{self._current_phase}': {str(e)}"
            self._status = ResearchStatus.FAILED

        result.completed_at = workflow.now()
        duration = (workflow.now() - start_time).total_seconds()

        return WorkflowOutput(
            result=result,
            workflow_id=input_data.workflow_id,
            duration_seconds=duration,
        )

    async def _expand_query(self, query: str) -> ExpandedQuery:
        """Expand the query for better research coverage.

        Args:
            query: Original research query

        Returns:
            ExpandedQuery with refined versions
        """
        workflow.logger.info(
            "expanding_query",
            extra={"query": query[:100]},
        )

        expanded = await workflow.execute_activity(
            expand_query_activity,
            args=[query, "", None],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=PLANNING_RETRY_POLICY,
        )

        # Add result event
        self._add_event(
            AgentEventType.AGENT_RESULT,
            "QueryExpansionAgent",
            f"💡 Query expanded: Identified intent as '{expanded.interpreted_intent[:80]}...' with {len(expanded.search_terms)} search terms.",
            {
                "interpreted_intent": expanded.interpreted_intent,
                "num_expanded_queries": len(expanded.expanded_queries),
                "num_search_terms": len(expanded.search_terms),
                "related_topics": expanded.related_topics[:5],
            },
        )

        workflow.logger.info(
            "query_expanded",
            extra={
                "num_expanded": len(expanded.expanded_queries),
                "num_terms": len(expanded.search_terms),
            },
        )

        return expanded

    async def _create_plan(
        self,
        original_query: str,
        expanded_query: ExpandedQuery,
    ) -> ResearchPlan:
        """Create a structured research plan.

        Args:
            original_query: Original query
            expanded_query: Expanded query information

        Returns:
            ResearchPlan with sub-tasks
        """
        context = (
            f"Interpreted intent: {expanded_query.interpreted_intent}\n"
            f"Related topics: {', '.join(expanded_query.related_topics[:5])}\n"
            f"Suggested search terms: {', '.join(expanded_query.search_terms[:10])}"
        )

        workflow.logger.info(
            "creating_research_plan",
            extra={"query": original_query[:100]},
        )

        plan = await workflow.execute_activity(
            create_research_plan_activity,
            args=[original_query, context],
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=PLANNING_RETRY_POLICY,
        )

        # Add result event
        task_descriptions = [t.description[:50] for t in plan.sub_tasks[:3]]
        self._add_event(
            AgentEventType.AGENT_RESULT,
            "PlanningAgent",
            f"📝 Research plan created with {len(plan.sub_tasks)} tasks. Key entities: {', '.join(plan.key_entities[:3])}",
            {
                "num_tasks": len(plan.sub_tasks),
                "key_entities": plan.key_entities,
                "task_previews": task_descriptions,
                "query_analysis": plan.query_analysis[:200],
            },
        )

        workflow.logger.info(
            "research_plan_created",
            extra={
                "num_tasks": len(plan.sub_tasks),
                "num_entities": len(plan.key_entities),
            },
        )

        return plan

    async def _execute_research_loop(
        self,
        original_query: str,
        max_iterations: int,
    ) -> None:
        """Execute research with validation and improvement loop.

        Args:
            original_query: The original research query
            max_iterations: Maximum research iterations
        """
        # Execute research on plan sub-tasks
        await self._execute_plan_tasks(original_query, max_iterations)

        # Validation and improvement loop (max 2 improvement cycles)
        max_improvement_cycles = 2
        for cycle in range(max_improvement_cycles):
            self._iteration_count = cycle + 1

            # Validate current research
            validation = await self._validate_research(original_query)
            self._validation_results.append(validation)

            if validation.is_valid and validation.completeness_score >= 0.8:
                workflow.logger.info(
                    "research_validated",
                    extra={
                        "cycle": cycle + 1,
                        "completeness": validation.completeness_score,
                    },
                )
                break

            # Check if there are gaps to fill via additional research
            if not validation.additional_queries and not validation.unanswered_parts:
                workflow.logger.info(
                    "validation_no_gaps",
                    extra={"cycle": cycle + 1, "completeness": validation.completeness_score},
                )
                break

            # Execute additional research based on validation feedback
            await self._execute_improvement_research(
                original_query,
                validation,
                max_iterations,
            )

    async def _execute_plan_tasks(
        self,
        original_query: str,
        max_iterations: int,
    ) -> None:
        """Execute research tasks from the plan.

        Args:
            original_query: Original query
            max_iterations: Max iterations to use
        """
        if not self._research_plan:
            # Fallback to simple research if no plan
            await self._simple_research(original_query, max_iterations)
            return

        # Get ready tasks (dependencies met)
        tasks_to_execute = self._research_plan.get_ready_tasks()
        iteration = 1

        while tasks_to_execute and iteration <= max_iterations:
            task = tasks_to_execute[0]  # Take highest priority ready task

            workflow.logger.info(
                "executing_research_task",
                extra={
                    "task_id": task.task_id,
                    "description": task.description[:100],
                    "iteration": iteration,
                },
            )

            # Add thinking event
            self._add_event(
                AgentEventType.AGENT_THINKING,
                "ResearchAgent",
                f"🔍 Researching task {iteration}: {task.description[:80]}...",
                {"task_id": task.task_id, "iteration": iteration},
            )

            # Build context from previous findings
            context = self._build_research_context()

            # Use task's search queries or description
            research_query = (
                task.search_queries[0]
                if task.search_queries
                else task.description
            )

            research_step = await workflow.execute_activity(
                conduct_research_activity,
                args=[research_query, iteration, context],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RESEARCH_RETRY_POLICY,
            )

            self._research_steps.append(research_step)

            # Add result event
            self._add_event(
                AgentEventType.AGENT_RESULT,
                "ResearchAgent",
                f"📄 Found {len(research_step.sources)} sources with {research_step.confidence:.0%} confidence: {research_step.findings[:150]}...",
                {
                    "task_id": task.task_id,
                    "iteration": iteration,
                    "confidence": research_step.confidence,
                    "num_sources": len(research_step.sources),
                    "findings_preview": research_step.findings[:300],
                },
            )

            # Mark task as completed in plan
            task.is_completed = True
            task.findings = research_step.findings[:500]

            # Get next ready tasks
            tasks_to_execute = self._research_plan.get_ready_tasks()
            iteration += 1

    async def _simple_research(
        self,
        query: str,
        max_iterations: int,
    ) -> None:
        """Simple research without a plan (fallback).

        Args:
            query: Research query
            max_iterations: Max iterations
        """
        current_query = query

        for iteration in range(1, max_iterations + 1):
            context = self._build_research_context()

            research_step = await workflow.execute_activity(
                conduct_research_activity,
                args=[current_query, iteration, context],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RESEARCH_RETRY_POLICY,
            )

            self._research_steps.append(research_step)

            if not research_step.requires_followup:
                break

            if research_step.followup_questions:
                current_query = research_step.followup_questions[0]

    async def _validate_research(
        self,
        original_query: str,
    ) -> ValidationResult:
        """Validate current research findings.

        Args:
            original_query: Original query

        Returns:
            ValidationResult
        """
        workflow.logger.info(
            "validating_research",
            extra={"num_steps": len(self._research_steps)},
        )

        # Add validation start event
        self._add_event(
            AgentEventType.AGENT_START,
            "ValidationAgent",
            "🔎 Validating research completeness and accuracy...",
        )

        validation = await workflow.execute_activity(
            validate_research_activity,
            args=[
                original_query,
                self._research_steps,
                self._research_plan,
                "",  # No summary yet
            ],
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=VALIDATION_RETRY_POLICY,
        )

        # Add validation result event
        status_emoji = "✅" if validation.is_valid else "⚠️"
        self._add_event(
            AgentEventType.VALIDATION,
            "ValidationAgent",
            f"{status_emoji} Validation: {validation.completeness_score:.0%} complete, {len(validation.issues)} issues found",
            {
                "is_valid": validation.is_valid,
                "completeness_score": validation.completeness_score,
                "accuracy_score": validation.accuracy_score,
                "num_issues": len(validation.issues),
                "unanswered_parts": validation.unanswered_parts[:3],
            },
        )

        workflow.logger.info(
            "validation_complete",
            extra={
                "is_valid": validation.is_valid,
                "completeness": validation.completeness_score,
                "num_issues": len(validation.issues),
            },
        )

        return validation

    async def _execute_improvement_research(
        self,
        original_query: str,
        validation: ValidationResult,
        max_iterations: int,
    ) -> None:
        """Execute additional research based on validation feedback.

        Args:
            original_query: Original query
            validation: Validation result with gaps and additional queries
            max_iterations: Max total iterations
        """
        # Determine what additional research is needed
        additional_queries: list[str] = []

        # First, use the specific additional queries from validation agent
        additional_queries.extend(validation.additional_queries[:2])

        # If no additional queries, use unanswered parts directly
        if not additional_queries:
            for part in validation.unanswered_parts[:2]:
                additional_queries.append(
                    f"{original_query} - specifically about: {part}"
                )

        # If still no queries, use recommendations
        if not additional_queries:
            for recommendation in validation.recommendations[:2]:
                additional_queries.append(
                    f"{original_query} - focusing on: {recommendation}"
                )

        if not additional_queries:
            workflow.logger.info(
                "no_additional_queries",
                extra={"validation_completeness": validation.completeness_score},
            )
            return

        # Add event for improvement research
        self._add_event(
            AgentEventType.AGENT_START,
            "ResearchAgent",
            f"🔄 Conducting additional research to fill {len(additional_queries)} identified gaps...",
            {"num_gaps": len(additional_queries), "queries": additional_queries[:3]},
        )

        # Execute additional research
        current_iteration = len(self._research_steps) + 1
        max_additional = min(2, max_iterations - current_iteration + 1)

        for i, query in enumerate(additional_queries[:max_additional]):
            context = self._build_research_context()

            workflow.logger.info(
                "executing_improvement_research",
                extra={
                    "query": query[:100],
                    "iteration": current_iteration + i,
                },
            )

            # Add thinking event
            self._add_event(
                AgentEventType.AGENT_THINKING,
                "ResearchAgent",
                f"🔍 Filling gap {i + 1}: {query[:80]}...",
                {"gap_number": i + 1, "query": query},
            )

            research_step = await workflow.execute_activity(
                conduct_research_activity,
                args=[query, current_iteration + i, context],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RESEARCH_RETRY_POLICY,
            )

            self._research_steps.append(research_step)

            # Add result event
            self._add_event(
                AgentEventType.AGENT_RESULT,
                "ResearchAgent",
                f"📄 Gap filled: Found {len(research_step.sources)} sources with {research_step.confidence:.0%} confidence.",
                {
                    "iteration": current_iteration + i,
                    "confidence": research_step.confidence,
                    "num_sources": len(research_step.sources),
                },
            )

    async def _create_interim_summary(self, original_query: str) -> str:
        """Create an interim summary for critique.

        Args:
            original_query: Original query

        Returns:
            Interim summary string
        """
        if not self._research_steps:
            return ""

        summary = await workflow.execute_activity(
            synthesize_findings_activity,
            args=[self._research_steps, original_query],
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=SYNTHESIS_RETRY_POLICY,
        )

        return summary

    async def _synthesize_with_quality_check(
        self,
        original_query: str,
    ) -> str:
        """Create final synthesis with quality validation.

        Args:
            original_query: Original query

        Returns:
            Final summary
        """
        workflow.logger.info(
            "creating_final_synthesis",
            extra={"num_steps": len(self._research_steps)},
        )

        summary = await workflow.execute_activity(
            synthesize_findings_activity,
            args=[self._research_steps, original_query],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=SYNTHESIS_RETRY_POLICY,
        )

        # Add synthesis result event
        self._add_event(
            AgentEventType.AGENT_RESULT,
            "SynthesisAgent",
            f"📝 Final summary created ({len(summary)} characters) combining findings from {len(self._research_steps)} research steps.",
            {
                "summary_length": len(summary),
                "num_steps_synthesized": len(self._research_steps),
                "summary_preview": summary[:300],
            },
        )

        workflow.logger.info(
            "final_synthesis_complete",
            extra={"summary_length": len(summary)},
        )

        return summary

    def _build_research_context(self) -> str:
        """Build context from previous research steps.

        Returns:
            Context string
        """
        if not self._research_steps:
            return ""

        recent_steps = self._research_steps[-3:]
        context_parts: list[str] = []

        for step in recent_steps:
            summary = (
                step.findings[:500]
                if len(step.findings) > 500
                else step.findings
            )
            context_parts.append(
                f"[Previous finding - confidence: {step.confidence:.0%}]: {summary}"
            )

        return "\n\n".join(context_parts)

    @workflow.query
    def get_status(self) -> dict[str, Any]:
        """Query current workflow status.

        Returns:
            Status information
        """
        return {
            "status": self._status.value,
            "current_phase": self._current_phase,
            "research_steps": len(self._research_steps),
            "validation_iterations": len(self._validation_results),
            "plan_tasks": (
                len(self._research_plan.sub_tasks) if self._research_plan else 0
            ),
            "plan_completion": (
                self._research_plan.completion_percentage()
                if self._research_plan
                else 0.0
            ),
        }

    @workflow.query
    def get_plan(self) -> dict[str, Any] | None:
        """Query the research plan.

        Returns:
            Plan summary or None
        """
        if not self._research_plan:
            return None

        return {
            "original_query": self._research_plan.original_query,
            "query_analysis": self._research_plan.query_analysis,
            "key_entities": self._research_plan.key_entities,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "priority": t.priority,
                    "is_completed": t.is_completed,
                }
                for t in self._research_plan.sub_tasks
            ],
            "completion_percentage": self._research_plan.completion_percentage(),
        }

    @workflow.query
    def get_validation_history(self) -> list[dict[str, Any]]:
        """Query validation history.

        Returns:
            List of validation summaries
        """
        return [
            {
                "is_valid": v.is_valid,
                "completeness_score": v.completeness_score,
                "accuracy_score": v.accuracy_score,
                "num_issues": len(v.issues),
                "has_critical": v.has_critical_issues(),
                "unanswered_parts": v.unanswered_parts,
                "additional_queries": v.additional_queries,
            }
            for v in self._validation_results
        ]

    @workflow.query
    def get_agent_events(self) -> list[dict[str, Any]]:
        """Query agent events for chat-style display.

        Returns:
            List of agent events with all details
        """
        return [
            {
                "event_id": str(event.event_id),
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "agent_name": event.agent_name,
                "message": event.message,
                "details": event.details,
                "phase": event.phase,
            }
            for event in self._agent_events
        ]
