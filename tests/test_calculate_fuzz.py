"""Fuzzing the calculator tool: property testing's cousin.

The tool wraps eval() in a restricted namespace. Random strings should never
escape as an exception, and simple arithmetic should agree with Python.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deep_research_poc.agents.tools import calculate


@pytest.mark.asyncio
@settings(max_examples=300, deadline=None)
@given(st.text(max_size=40))
async def test_calculate_never_raises(expression: str) -> None:
    out = await calculate(expression)
    assert out.startswith(("Result: ", "Calculation failed: "))


@pytest.mark.asyncio
@settings(deadline=None)
@given(st.integers(-1000, 1000), st.integers(-1000, 1000), st.sampled_from("+-*"))
async def test_calculate_agrees_with_python(a: int, b: int, op: str) -> None:
    out = await calculate(f"{a} {op} {b}")
    assert out == f"Result: {eval(f'{a} {op} {b}')}"  # noqa: S307
