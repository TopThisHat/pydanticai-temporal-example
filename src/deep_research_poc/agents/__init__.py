"""Multi-agent architecture for deep research.

This package contains specialized agents that work together to conduct
comprehensive research with planning and validation loops.

Available agents:
- ResearchAgent: Conducts research with tool-augmented investigation
- PlanningAgent: Breaks down queries into research sub-tasks
- ValidationAgent: Validates if all parts of the query are answered and suggests
  additional research to fill gaps
- QueryExpansionAgent: Refines and expands queries
"""

from deep_research_poc.agents.base import BaseSpecializedAgent
from deep_research_poc.agents.planning import PlanningAgent, create_planning_agent
from deep_research_poc.agents.query_expansion import (
    QueryExpansionAgent,
    create_query_expansion_agent,
)
from deep_research_poc.agents.research import (
    ResearchAgent,
    ResearchContext,
    create_research_agent,
)
from deep_research_poc.agents.tools import (
    calculate,
    fetch_url,
    get_current_datetime,
    web_search,
    wikipedia_search,
)
from deep_research_poc.agents.validation import ValidationAgent, create_validation_agent

__all__ = [
    # Base
    "BaseSpecializedAgent",
    # Research agent
    "ResearchAgent",
    "ResearchContext",
    "create_research_agent",
    # Planning agent
    "PlanningAgent",
    "create_planning_agent",
    # Validation agent
    "ValidationAgent",
    "create_validation_agent",
    # Query expansion agent
    "QueryExpansionAgent",
    "create_query_expansion_agent",
    # Tools
    "calculate",
    "fetch_url",
    "get_current_datetime",
    "web_search",
    "wikipedia_search",
]
