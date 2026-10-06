# How I Trust Code I Didn't Write

*Property testing in the age of AI*

I built the project this post is about with Claude Code. A deep-research agent: a Temporal workflow that fans a question out to planning, research, validation and critique agents, then stitches the answers back together. It's a few thousand lines of Python. I have read maybe a third of it closely.

That's not a confession. It's the new normal, and I think it's fine. AI is great at writing code. What it is not great at, yet, is knowing what *correct* means for your code. Someone still has to say that out loud, and the clearest way I've found to say it is a test that checks a property instead of an example.

This post is about that technique, and about the two testing tools I reach for next to it. Everything below actually runs; the code is in the repo at the end.

## The weak layer

When I review AI-written code I think in layers, bottom to top:

1. **Types and schemas.** Pydantic models, type hints. They catch the shape of a mistake.
2. **Example tests.** `assert f(2) == 4`. The AI writes these for free.
3. **Property tests.** For *all* inputs, something holds.
4. **Mutation testing.** Deliberately break the code and check the tests notice.
5. **Stateful tests.** Random sequences of operations against invariants.
6. **Human review.** Me, reading.

Layer 2 used to be the backbone. In the AI age, it's the weak one.

Here's why. When I ask a coding agent to "add tests," it writes tests that pass against the code it just wrote. Of course it does. The tests and the code came out of the same model, in the same sitting, from the same understanding of the problem. If that understanding is wrong, the tests are wrong in exactly the same way. They pass. They're green. They tell you almost nothing.

A property test is different in kind. It doesn't say "this input gives this output." It says "no matter what you feed this function, *this* must remain true." That's a statement about the problem, not the implementation, and the agent can't satisfy it by accident.

Layers 3 through 5 are how you get the signal back. Layer 6 is still there; it's just last, not first, and it's not enough on its own.

## The toy

Start with the smallest possible example so the mechanics are clear. A function that removes duplicates from a list while keeping the first occurrence of each item in place:

```python
def dedupe_keep_order(items: list[str]) -> list[str]:
    return list(set(items))
```

If you've written Python for a while you already see the bug. Pretend you don't; pretend an agent wrote it at 11pm and it's one of forty functions in the diff.

An example test is easy to write and easy to fool:

```python
def test_dedupe():
    assert dedupe_keep_order(["a", "a", "b"]) == ["a", "b"]
```

That passes. Sets of small strings happen to iterate in an order that matches here. Green.

Now say what `dedupe_keep_order` is actually *for*, as properties. Three things should hold for any list:

```python
from hypothesis import given, strategies as st


@given(st.lists(st.text()))
def test_dedupe_has_no_duplicates(items):
    out = dedupe_keep_order(items)
    assert len(out) == len(set(out))


@given(st.lists(st.text()))
def test_dedupe_loses_nothing(items):
    assert set(dedupe_keep_order(items)) == set(items)


@given(st.lists(st.text()))
def test_dedupe_keeps_first_seen_order(items):
    out = dedupe_keep_order(items)
    first_seen = []
    for x in items:
        if x not in first_seen:
            first_seen.append(x)
    assert out == first_seen
```

`@given(st.lists(st.text()))` tells [Hypothesis](https://hypothesis.readthedocs.io/) to generate lists of strings, hundreds of them, and run the test on each. The first two properties pass. The third does not:

```
    @given(st.lists(st.text()))
    def test_dedupe_keeps_first_seen_order(items):
        ...
>       assert out == first_seen
E       AssertionError: assert ['', '0'] == ['0', '']
E       Failing test case: test_dedupe_keeps_first_seen_order(
E           items=['0', ''],
E       )
```

Look at what it handed back. Not some forty-element list of Unicode garbage. `['0', '']`. Two strings, the two shortest it could find, in an order the function doesn't preserve. Hypothesis found a failure and then *shrank* it, trying smaller and smaller inputs until it had the minimal case that still breaks. That shrunk example is the whole pitch. It's the bug report you wish your users wrote.

The fix is one line (`list(dict.fromkeys(items))`), and once you've written the three properties, you never have to think about this function again. Any future rewrite, by you or by an agent, has to satisfy them.

(If you write TypeScript, [fast-check](https://fast-check.dev/) is the same idea with the same shrinking; everything in this post translates.)

## The real thing

The toy was `dedupe_keep_order`. The project has the same function in disguise. A research run produces a list of steps, each with its own sources, and the final report needs one de-duplicated list of citations across all of them:

```python
class ResearchResult(BaseModel):
    ...
    @property
    def all_sources(self) -> list[Source]:
        """Aggregate all unique sources from all research steps."""
        seen_urls: set[str] = set()
        unique_sources: list[Source] = []
        for step in self.steps:
            for source in step.sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    unique_sources.append(source)
        return unique_sources
```

Claude wrote this. It's correct. There were no tests for it.

The properties are the same three as the toy, plus one I'll explain in a moment. The only new work is telling Hypothesis how to build a `ResearchResult`:

```python
# A small URL alphabet makes duplicates across steps likely,
# which is the interesting case for de-duplication.
urls = st.sampled_from([f"https://example.com/{i}" for i in range(8)])

sources = st.builds(Source, url=urls, title=st.text(max_size=20),
                    description=st.text(max_size=40))

steps = st.builds(ResearchStep,
                  iteration=st.integers(min_value=1, max_value=20),
                  question=st.text(min_size=1, max_size=50),
                  findings=st.text(max_size=100),
                  sources=st.lists(sources, max_size=5),
                  confidence=st.floats(min_value=0.0, max_value=1.0))

results = st.builds(ResearchResult,
                    query=st.text(min_size=1, max_size=50),
                    steps=st.lists(steps, max_size=6))
```

`st.builds` takes a class and a strategy per field, and Hypothesis fills in anything with a default on its own. The comment on `urls` matters: if you let Hypothesis generate arbitrary URLs, it will almost never produce two the same, and your de-duplication code will never actually de-duplicate anything. Choosing a tiny alphabet is how you steer it toward the collisions you care about. That's most of the craft in property testing: picking generators that make the interesting cases common.

Then the properties:

```python
@given(results)
def test_all_sources_has_no_duplicate_urls(result):
    urls_seen = [s.url for s in result.all_sources]
    assert len(urls_seen) == len(set(urls_seen))


@given(results)
def test_all_sources_loses_nothing(result):
    expected = {s.url for step in result.steps for s in step.sources}
    assert {s.url for s in result.all_sources} == expected


@given(results)
def test_all_sources_keeps_first_seen_order(result):
    first_seen = []
    for step in result.steps:
        for s in step.sources:
            if s.url not in first_seen:
                first_seen.append(s.url)
    assert [s.url for s in result.all_sources] == first_seen


@given(results)
def test_all_sources_is_idempotent(result):
    """Feeding the de-duplicated list back in as one step changes nothing."""
    once = result.all_sources
    one_step = ResearchStep(iteration=1, question="q", findings="",
                            confidence=1.0, sources=once)
    again = result.model_copy(update={"steps": [one_step]}).all_sources
    assert again == once
```

Idempotence is the one I'd recommend adding to any "clean up a collection" function. It says: once this has run, running it again is a no-op. It's cheap to state and it catches a surprising family of off-by-one and ordering bugs.

### Breaking it on purpose

The code was correct, so to show you the tests doing their job I asked Claude to introduce a subtle bug. I want to be clear that this is a plant; it's not a bug the agent made on its own. It moved one line:

```python
        unique_sources: list[Source] = []
        for step in self.steps:
            seen_urls: set[str] = set()      # <- was above the loop
            for source in step.sources:
```

That's a very believable refactor slip. Sources are now de-duplicated *within* a step but not *across* steps. Every example test you'd naturally write, with one step and a repeated URL, still passes.

Three of the four properties fail. Here's the shrunk case from the first:

```
E       Failing test case: test_all_sources_has_no_duplicate_urls(
E           # The test always failed when commented parts were varied together.
E           result=ResearchResult(
E               query='0',  # or any other generated value
E               steps=[ResearchStep(
E                    iteration=1,  # or any other generated value
E                    question='0',  # or any other generated value
E                    findings='',  # or any other generated value
E                    sources=[Source(
E                         url='https://example.com/0',
E                         title='',  # or any other generated value
E                         description='',  # or any other generated value
E                     )],
E                    confidence=0.0,
E                ), ResearchStep(
E                    ...
E                    sources=[Source(
E                         url='https://example.com/0',
E                         ...
E                     )],
E                )],
E           ),
E       )
```

Two steps. One source each. Same URL. And read the annotations: `# or any other generated value` on every field that *doesn't* matter. Hypothesis is telling you the exact shape of the bug: it's about two steps sharing a URL, and nothing else. That's a better diagnosis than I'd get from most humans, and it took under two seconds.

## The test that found a design smell

Not everything Hypothesis finds is a bug. Sometimes it's a decision nobody made on purpose.

A `ResearchQuery` has a `max_iterations` (default 3) and a `depth` of `quick`, `standard` or `deep`. There's a validator that bumps the iteration count to match the depth, but only if the user didn't set it explicitly:

```python
@model_validator(mode="after")
def adjust_iterations_by_depth(self) -> "ResearchQuery":
    depth_defaults = {"quick": 1, "standard": 3, "deep": 5}
    # Only adjust if using default value
    if self.max_iterations == 3 and self.depth != "standard":
        object.__setattr__(self, "max_iterations", depth_defaults[self.depth])
    return self
```

The property is obvious: if I set `max_iterations` explicitly, it should be respected.

```python
@given(st.integers(min_value=1, max_value=10), depths)
def test_explicit_iterations_are_respected(max_iterations, depth):
    q = ResearchQuery(query="q", max_iterations=max_iterations, depth=depth)
    assert q.max_iterations == max_iterations
```

It fails instantly, on `max_iterations=3, depth="deep"`, and you can see why from the source. The validator can't tell "the user asked for 3" from "the user didn't say." It uses the value 3 as a sentinel for *unset*. A user who explicitly wants three deep iterations gets five.

Is that a bug? Arguably it's a reasonable heuristic. But it's a decision that was never made; the agent reached for the simplest thing that satisfied the docstring, and the docstring was ambiguous. The real problem is that "unset" wasn't representable, so the code borrowed a real value to mean it.

The fix is to make the absence a real state:

```python
max_iterations: int | None = Field(default=None, ge=1, le=10, ...)

@model_validator(mode="after")
def adjust_iterations_by_depth(self) -> "ResearchQuery":
    depth_defaults = {"quick": 1, "standard": 3, "deep": 5}
    if self.max_iterations is None:
        object.__setattr__(self, "max_iterations", depth_defaults[self.depth])
    return self
```

Now an explicit 3 is a 3, the API schema defaults to `None` so depth still drives the default for callers who don't care, and the property passes for every value. I added its mirror image too, "unset follows depth," so both halves of the contract are pinned:

```python
@given(depths)
def test_unset_iterations_follow_depth(depth):
    q = ResearchQuery(query="q", depth=depth)
    assert q.iterations == {"quick": 1, "standard": 3, "deep": 5}[depth]
```

That's a two-line change to the model and a one-line change to the API, and I wouldn't have made it without the test, because the old behaviour looked fine in every example anyone had thought to write.

This is the part of property testing I didn't expect: it doesn't just find bugs, it forces the ambiguous questions out of the code and onto the table, where a person can answer them.

## Do your tests actually catch anything?

Property tests are my layer 3. Layer 4 asks a question that nothing else can: *if the code were wrong, would these tests notice?*

Mutation testing answers it by brute force. A tool takes your source, makes one small change (flip a `<` to `<=`, replace a constant, swap `and` for `or`), runs the tests, and records whether anything failed. If a test fails, the mutant is "killed." If everything stays green, it "survived," and you've found code your tests don't constrain. Repeat for every mutation the tool can think of.

I ran [mutmut](https://mutmut.readthedocs.io/) over `models.py`, the file with all the pure logic in this project. First with the only tests that existed for it, five example-based tests the agent had written, and then with the property tests added.

| Test suite | Mutants killed | Survived | Never reached |
|---|---|---|---|
| Example tests (5, AI-written) | 20 / 44 | 0 | 24 |
| Property tests (first pass) | 39 / 44 | 4 | 1 |
| Property tests (final) | 43 / 44 | 1 | 0 |

The first row is the "layer 2 is weak" argument in one line. Twenty-four mutants were never even *reached*: whole functions with no test touching them. The example tests looked fine. Each one tested a real behaviour with a real assertion. They just covered a small, hand-picked slice of the file and left the rest untouched. That's the failure mode of AI-written tests: not that they're wrong, but that they're narrow in a way that's invisible until you measure it.

The middle row is the interesting one. My first pass of property tests left four survivors, all on the same line:

```diff
-        citation = f"[{i}] {source.title or 'Untitled'}"
+        citation = f"[{i}] {source.title or 'XXUntitledXX'}"
```

I'd written a property that the citation numbering was `[1]`, `[2]`, `[3]`... and never one that said the title had to be in there. Mutation testing caught *my* gap, in a test I'd just written and was pleased with. That's the second argument for layer 4: it audits layer 3 too, and property tests are not immune to being too loose.

The last row has one survivor, and it's worth looking at:

```diff
     def completion_percentage(self) -> float:
         if not self.sub_tasks:
-            return 0.0
+            return 1.0
```

No test can kill this, because no test can reach it. `sub_tasks` is declared with `min_length=1` in the Pydantic model, so a plan with zero sub-tasks can't be constructed. The guard is dead code. That's called an *equivalent mutant*, and when you hit one you have two honest options: delete the dead branch, or leave the mutant surviving and write down why. I left it, because deleting the guard makes the function look unsafe to a reader who doesn't know the schema. A 43/44 with a reason beats a 44/44 bought by removing a defensive line.

One caveat on the numbers: mutmut skips decorated functions, so `all_sources` (a `@property`) and the validator above aren't in the 44. They're tested; they're just not audited by this tool. Know what your score counts.

## Testing the thing that changes over time

The models so far are value objects: build one, ask it a question, done. A Temporal workflow isn't like that. A `ResearchPlan` lives for minutes or hours while tasks get added, completed, and queried. The bugs there are sequence bugs: "this is wrong *after* you do A, then B, then A again."

Hypothesis has a tool for that, and it's my layer 5. You describe the operations as rules and the things that must always be true as invariants, and it generates random sequences of operations, checking the invariants after every step:

```python
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule


class PlanMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.plan = ResearchPlan(original_query="q", query_analysis="a",
                                 sub_tasks=[ResearchSubTask(task_id="t0", description="seed")])

    @rule(deps=st.lists(st.integers(min_value=0, max_value=5), max_size=2))
    def add_task(self, deps):
        existing = [t.task_id for t in self.plan.sub_tasks]
        self.plan.sub_tasks.append(ResearchSubTask(
            task_id=f"t{len(existing)}", description="d",
            dependencies=[existing[i % len(existing)] for i in deps]))

    @precondition(lambda self: self.plan.get_ready_tasks())
    @rule(data=st.data())
    def complete_ready_task(self, data):
        task = data.draw(st.sampled_from(self.plan.get_ready_tasks()))
        task.is_completed = True

    @invariant()
    def ready_is_subset_of_pending(self):
        pending = {id(t) for t in self.plan.get_pending_tasks()}
        assert all(id(t) in pending for t in self.plan.get_ready_tasks())

    @invariant()
    def ready_tasks_have_completed_dependencies(self):
        done = {t.task_id for t in self.plan.sub_tasks if t.is_completed}
        for task in self.plan.get_ready_tasks():
            assert set(task.dependencies) <= done

    @invariant()
    def percentage_is_consistent(self):
        pct = self.plan.completion_percentage()
        assert 0.0 <= pct <= 100.0
        assert (pct == 100.0) == (not self.plan.get_pending_tasks())


TestPlanMachine = PlanMachine.TestCase
```

Twenty-five lines. Two operations, three invariants. Hypothesis will add tasks with random dependency graphs, complete them in random valid orders, and after every single step confirm that "ready" tasks are a subset of "pending" ones, that nothing is ready while its dependencies are open, and that the percentage hits 100 exactly when nothing is left. If it ever finds a sequence that breaks one, it shrinks that too: down to the shortest sequence of operations that reproduces it.

This one passes. The point isn't the catch; it's that I now have a precise, executable statement of what a research plan *is*, written in about the time it takes to write three example tests, and it'll outlive every reimplementation.

## A cameo: fuzzing the thing with `eval` in it

Property testing has a rougher cousin, fuzzing, which is the same idea with less structure: throw noise at it and see if it crashes. There's a calculator tool in this project that the agents can call, and it is implemented with `eval`, in a restricted namespace, wrapped in a try/except that promises to never raise. That's exactly the kind of promise worth throwing noise at:

```python
@pytest.mark.asyncio
@settings(max_examples=300, deadline=None)
@given(st.text(max_size=40))
async def test_calculate_never_raises(expression):
    out = await calculate(expression)
    assert out.startswith(("Result: ", "Calculation failed: "))
```

Three hundred random strings, including the ones that look like Python. It held. I'm still not thrilled about `eval` being in there, but "a property test says it doesn't escape" is a much better place to be than "I read it and it looked fine."

## What this changes about working with an agent

Here's the loop I actually run now.

I describe the feature. The agent writes the code and some example tests. I don't read the example tests closely; I treat them as smoke. Then I write the properties, or increasingly I ask the agent to *propose* properties and I edit them, which is a much better use of my attention than reading forty functions. Properties are short, they're about the problem rather than the solution, and a wrong one is obvious in a way a wrong example rarely is.

Then I run the mutation score, because the properties can be too loose and the tool will tell me where.

What I've noticed is that the agent gets better at the code when the properties exist first. "Make `all_sources` satisfy these four invariants" is a far better prompt than "aggregate the unique sources." It's a spec. It's executable. And when the agent gets it wrong, the shrunk counterexample goes straight back into the next prompt, which is a tighter feedback loop than anything I can produce by reading.

That's the real claim of this post. Property tests, mutation scores, and stateful models aren't just defence against AI-written code. They're how you *tell* an AI what correct means, in a language it can't talk its way around. The agent is great. The layers are what let me say that with a straight face.

---

The code in this post is real and lives in [the repo](https://github.com/TopThisHat/pydanticai-temporal-example): `tests/test_properties.py`, `tests/test_plan_state_machine.py` and `tests/test_calculate_fuzz.py`, with `make mutate` to reproduce the table. The planted bug is not committed; everything else is.
