"""FastAPI application for deep research workflows.

This module provides a REST API for starting and managing deep research
workflows using the multi-agent architecture with Temporal orchestration.
"""

from __future__ import annotations

from deep_research_poc.api.app import create_app

__all__ = ["create_app"]
