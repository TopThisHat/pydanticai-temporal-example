"""Stateful (model-based) test for ResearchPlan.

Hypothesis drives the plan through random sequences of operations and checks
the invariants after every step, the way a Temporal workflow would mutate it
over time.
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from deep_research_poc.models import ResearchPlan, ResearchSubTask


class PlanMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.plan = ResearchPlan(
            original_query="q",
            query_analysis="a",
            sub_tasks=[ResearchSubTask(task_id="t0", description="seed")],
        )

    @rule(deps=st.lists(st.integers(min_value=0, max_value=5), max_size=2))
    def add_task(self, deps: list[int]) -> None:
        existing = [t.task_id for t in self.plan.sub_tasks]
        task = ResearchSubTask(
            task_id=f"t{len(existing)}",
            description="d",
            dependencies=[existing[i % len(existing)] for i in deps],
        )
        self.plan.sub_tasks.append(task)

    @precondition(lambda self: self.plan.get_ready_tasks())
    @rule(data=st.data())
    def complete_ready_task(self, data: st.DataObject) -> None:
        task = data.draw(st.sampled_from(self.plan.get_ready_tasks()))
        task.is_completed = True
        task.findings = "done"

    @invariant()
    def ready_is_subset_of_pending(self) -> None:
        pending = {id(t) for t in self.plan.get_pending_tasks()}
        assert all(id(t) in pending for t in self.plan.get_ready_tasks())

    @invariant()
    def ready_tasks_have_completed_dependencies(self) -> None:
        done = {t.task_id for t in self.plan.sub_tasks if t.is_completed}
        for task in self.plan.get_ready_tasks():
            assert set(task.dependencies) <= done

    @invariant()
    def percentage_is_consistent(self) -> None:
        pct = self.plan.completion_percentage()
        assert 0.0 <= pct <= 100.0
        assert (pct == 100.0) == (not self.plan.get_pending_tasks())


TestPlanMachine = PlanMachine.TestCase
