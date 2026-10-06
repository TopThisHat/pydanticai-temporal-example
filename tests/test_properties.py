"""Property-based tests for the research models.

Instead of hand-picking examples, these tests state invariants that must hold
for *every* input and let Hypothesis search for one that breaks them.
"""

from __future__ import annotations

import re

from hypothesis import given
from hypothesis import strategies as st

from deep_research_poc.models import (
    ResearchPlan,
    ResearchQuery,
    ResearchResult,
    ResearchStep,
    ResearchSubTask,
    Source,
    ValidationIssue,
    ValidationResult,
)

# --------------------------------------------------------------------------
# Strategies: how to generate random-but-valid instances of our models.
# --------------------------------------------------------------------------

# A small URL alphabet makes duplicates across steps likely, which is the
# interesting case for de-duplication.
urls = st.sampled_from([f"https://example.com/{i}" for i in range(8)])

sources = st.builds(
    Source,
    url=urls,
    title=st.text(max_size=20),
    description=st.text(max_size=40),
)

steps = st.builds(
    ResearchStep,
    iteration=st.integers(min_value=1, max_value=20),
    question=st.text(min_size=1, max_size=50),
    findings=st.text(max_size=100),
    sources=st.lists(sources, max_size=5),
    confidence=st.floats(min_value=0.0, max_value=1.0),
)

results = st.builds(
    ResearchResult,
    query=st.text(min_size=1, max_size=50),
    steps=st.lists(steps, max_size=6),
)


# --------------------------------------------------------------------------
# ResearchResult.all_sources
# --------------------------------------------------------------------------


@given(results)
def test_all_sources_has_no_duplicate_urls(result: ResearchResult) -> None:
    urls_seen = [s.url for s in result.all_sources]
    assert len(urls_seen) == len(set(urls_seen))


@given(results)
def test_all_sources_loses_nothing(result: ResearchResult) -> None:
    expected = {s.url for step in result.steps for s in step.sources}
    assert {s.url for s in result.all_sources} == expected


@given(results)
def test_all_sources_keeps_first_seen_order(result: ResearchResult) -> None:
    first_seen: list[str] = []
    for step in result.steps:
        for s in step.sources:
            if s.url not in first_seen:
                first_seen.append(s.url)
    assert [s.url for s in result.all_sources] == first_seen


@given(results)
def test_all_sources_is_idempotent(result: ResearchResult) -> None:
    """Feeding the de-duplicated list back in as one step changes nothing."""
    once = result.all_sources
    one_step = ResearchStep(iteration=1, question="q", findings="", confidence=1.0, sources=once)
    again = result.model_copy(update={"steps": [one_step]}).all_sources
    assert again == once


@given(results)
def test_citation_numbering_matches_source_count(result: ResearchResult) -> None:
    text = result.get_formatted_citations()
    n = len(result.all_sources)
    if n == 0:
        assert text == "No sources cited."
    else:
        assert re.findall(r"^\[(\d+)\]", text, flags=re.MULTILINE) == [
            str(i) for i in range(1, n + 1)
        ]


@given(results)
def test_every_citation_names_its_source(result: ResearchResult) -> None:
    """Added after mutation testing: the numbering test above let mutants that
    mangled the title line survive."""
    text = result.get_formatted_citations()
    for i, source in enumerate(result.all_sources, 1):
        assert f"[{i}] {source.title or 'Untitled'}" in text
        assert f"URL: {source.url}" in text


@given(steps)
def test_step_citation_list_matches_sources(step: ResearchStep) -> None:
    citations = step.get_citation_list()
    assert len(citations) == len(step.sources)
    assert all(s.url in c for s, c in zip(step.sources, citations))


@given(sources)
def test_timestamps_are_timezone_aware(source: Source) -> None:
    """Added after mutation testing: nothing pinned utcnow() to an aware datetime,
    and naive timestamps would serialise differently through Temporal."""
    assert source.accessed_at.tzinfo is not None


# --------------------------------------------------------------------------
# ResearchQuery.adjust_iterations_by_depth
# --------------------------------------------------------------------------

depths = st.sampled_from(["quick", "standard", "deep"])


@given(st.integers(min_value=1, max_value=10), depths)
def test_iterations_always_within_bounds(max_iterations: int, depth: str) -> None:
    q = ResearchQuery(query="q", max_iterations=max_iterations, depth=depth)
    assert 1 <= q.max_iterations <= 10


@given(st.integers(min_value=1, max_value=10), depths)
def test_explicit_iterations_are_respected(max_iterations: int, depth: str) -> None:
    """This failed on max_iterations=3, depth='deep' before 'unset' was made
    representable as None; see docs/property-testing-in-the-age-of-ai.md."""
    q = ResearchQuery(query="q", max_iterations=max_iterations, depth=depth)
    assert q.max_iterations == max_iterations


@given(depths)
def test_unset_iterations_follow_depth(depth: str) -> None:
    q = ResearchQuery(query="q", depth=depth)
    assert q.iterations == {"quick": 1, "standard": 3, "deep": 5}[depth]


@given(st.one_of(st.none(), st.integers(min_value=1, max_value=10)), depths)
def test_query_survives_json_round_trip(max_iterations: int | None, depth: str) -> None:
    """Temporal serialises these models; a lossy round-trip would corrupt history."""
    q = ResearchQuery(query="q", max_iterations=max_iterations, depth=depth)
    assert ResearchQuery.model_validate_json(q.model_dump_json()) == q


# --------------------------------------------------------------------------
# ResearchPlan helpers
# --------------------------------------------------------------------------

task_ids = st.sampled_from([f"t{i}" for i in range(6)])

sub_tasks = st.builds(
    ResearchSubTask,
    task_id=task_ids,
    description=st.just("d"),
    dependencies=st.lists(task_ids, max_size=3),
    is_completed=st.booleans(),
)

plans = st.builds(
    ResearchPlan,
    original_query=st.just("q"),
    query_analysis=st.just("a"),
    sub_tasks=st.lists(sub_tasks, min_size=1, max_size=6),
)


@given(plans)
def test_ready_tasks_are_a_subset_of_pending(plan: ResearchPlan) -> None:
    pending = {id(t) for t in plan.get_pending_tasks()}
    assert all(id(t) in pending for t in plan.get_ready_tasks())


@given(plans)
def test_completion_percentage_is_a_percentage(plan: ResearchPlan) -> None:
    pct = plan.completion_percentage()
    assert 0.0 <= pct <= 100.0
    assert (pct == 100.0) == (not plan.get_pending_tasks())


@given(plans, st.randoms())
def test_plan_helpers_ignore_task_order(plan: ResearchPlan, rnd) -> None:
    shuffled = list(plan.sub_tasks)
    rnd.shuffle(shuffled)
    other = plan.model_copy(update={"sub_tasks": shuffled})
    assert other.completion_percentage() == plan.completion_percentage()
    assert {t.task_id for t in other.get_ready_tasks()} == {
        t.task_id for t in plan.get_ready_tasks()
    }


# --------------------------------------------------------------------------
# ValidationResult helpers
# --------------------------------------------------------------------------

issues = st.builds(
    ValidationIssue,
    issue_type=st.just("missing_answer"),
    severity=st.sampled_from(["low", "medium", "high", "critical"]),
    description=st.just("d"),
    is_resolved=st.booleans(),
)

validations = st.builds(
    ValidationResult,
    is_valid=st.booleans(),
    completeness_score=st.floats(0.0, 1.0),
    accuracy_score=st.floats(0.0, 1.0),
    coverage_analysis=st.just("c"),
    issues=st.lists(issues, max_size=5),
)


@given(validations)
def test_critical_flag_matches_issue_severities(result: ValidationResult) -> None:
    assert result.has_critical_issues() == ("critical" in {i.severity for i in result.issues})


@given(validations)
def test_unresolved_issues_are_exactly_the_unresolved_ones(result: ValidationResult) -> None:
    unresolved = result.get_unresolved_issues()
    assert all(not i.is_resolved for i in unresolved)
    assert len(unresolved) == sum(1 for i in result.issues if not i.is_resolved)
