"""Deep Research POC - AI-powered research with Temporal.

This package provides a proof-of-concept for deep research workflows
using PydanticAI and Temporal for durable execution.

Example:
    ```python
    from deep_research_poc.models import ResearchQuery, WorkflowInput
    from deep_research_poc.starter import start_research_workflow
    
    result = await start_research_workflow(
        query="What are the latest developments in quantum computing?",
        max_iterations=3,
        depth="standard",
    )
    print(result.result.final_summary)
    ```
"""

__version__ = "1.0.0"

from deep_research_poc.models import (
    ResearchQuery,
    ResearchResult,
    ResearchStatus,
    ResearchStep,
    WorkflowInput,
    WorkflowOutput,
)

__all__ = [
    "__version__",
    "ResearchQuery",
    "ResearchResult",
    "ResearchStatus",
    "ResearchStep",
    "WorkflowInput",
    "WorkflowOutput",
]
