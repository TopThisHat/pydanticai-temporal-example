"""HTTP client for interacting with the Deep Research API.

Provides a clean interface to communicate with the FastAPI backend,
handling all HTTP operations and response parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class ResearchDepth(str, Enum):
    """Research depth options."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


@dataclass
class ResearchStatus:
    """Current status of a research workflow."""

    workflow_id: str
    status: str
    current_phase: str | None = None
    research_steps: int = 0
    validation_iterations: int = 0


@dataclass
class Source:
    """A citation source."""

    url: str
    title: str = ""
    description: str = ""
    accessed_at: str = ""


@dataclass
class ResearchStep:
    """A single research step."""

    step_id: str
    iteration: int
    question: str
    findings: str
    confidence: float
    sources: list[Source]
    timestamp: str


@dataclass
class ResearchResult:
    """Complete research result."""

    workflow_id: str
    query: str
    status: str
    final_summary: str
    total_iterations: int
    duration_seconds: float
    steps: list[ResearchStep]
    sources: list[Source]
    started_at: str
    completed_at: str | None = None


@dataclass
class AgentEvent:
    """An agent event for chat-style display."""

    event_id: str
    timestamp: str
    event_type: str
    agent_name: str
    message: str
    details: dict[str, Any]
    phase: str


class ResearchApiClient:
    """Client for interacting with the Deep Research API."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL of the API server.
        """
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=300.0)  # 5 min timeout for sync requests

    def check_health(self) -> dict[str, Any]:
        """Check API health status.

        Returns:
            Health status response.

        Raises:
            httpx.HTTPError: If the health check fails.
        """
        response = self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def start_research(
        self,
        query: str,
        depth: ResearchDepth = ResearchDepth.STANDARD,
        max_iterations: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Start a new research workflow.

        Args:
            query: The research question.
            depth: Research depth level.
            max_iterations: Maximum iterations.
            metadata: Additional metadata.

        Returns:
            The workflow ID.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        payload: dict[str, str | int | dict[str, Any]] = {
            "query": query,
            "depth": depth.value,
            "max_iterations": max_iterations,
            "metadata": metadata or {},
        }

        response = self._client.post(
            f"{self.base_url}/api/v1/research",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["workflow_id"])

    def get_status(self, workflow_id: str) -> ResearchStatus:
        """Get current workflow status.

        Args:
            workflow_id: The workflow ID to query.

        Returns:
            Current research status.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        response = self._client.get(
            f"{self.base_url}/api/v1/research/{workflow_id}/status"
        )
        response.raise_for_status()
        data = response.json()

        return ResearchStatus(
            workflow_id=data["workflow_id"],
            status=data["status"],
            current_phase=data.get("current_phase"),
            research_steps=data.get("research_steps", 0),
            validation_iterations=data.get("validation_iterations", 0),
        )

    def get_agent_events(self, workflow_id: str) -> list[AgentEvent]:
        """Get agent events for chat-style display.

        Args:
            workflow_id: The workflow ID to query.

        Returns:
            List of agent events in chronological order.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        response = self._client.get(
            f"{self.base_url}/api/v1/research/{workflow_id}/events"
        )
        response.raise_for_status()
        data = response.json()

        return [
            AgentEvent(
                event_id=e["event_id"],
                timestamp=e["timestamp"],
                event_type=e["event_type"],
                agent_name=e["agent_name"],
                message=e["message"],
                details=e.get("details", {}),
                phase=e.get("phase", ""),
            )
            for e in data.get("events", [])
        ]

    def get_result(self, workflow_id: str) -> ResearchResult | None:
        """Get complete research results.

        Args:
            workflow_id: The workflow ID to query.

        Returns:
            Research results if complete, None if still running.

        Raises:
            httpx.HTTPError: If the request fails (excluding 202).
        """
        response = self._client.get(
            f"{self.base_url}/api/v1/research/{workflow_id}"
        )

        # 202 means still in progress
        if response.status_code == 202:
            return None

        response.raise_for_status()
        data = response.json()

        return self._parse_result(data)

    def run_sync(
        self,
        query: str,
        depth: ResearchDepth = ResearchDepth.STANDARD,
        max_iterations: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchResult:
        """Run research synchronously and wait for results.

        Args:
            query: The research question.
            depth: Research depth level.
            max_iterations: Maximum iterations.
            metadata: Additional metadata.

        Returns:
            Complete research results.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        payload: dict[str, str | int | dict[str, Any]] = {
            "query": query,
            "depth": depth.value,
            "max_iterations": max_iterations,
            "metadata": metadata or {},
        }

        response = self._client.post(
            f"{self.base_url}/api/v1/research/sync",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return self._parse_result(data)

    def _parse_result(self, data: dict[str, Any]) -> ResearchResult:
        """Parse API response into ResearchResult."""
        sources = [
            Source(
                url=s.get("url", ""),
                title=s.get("title", ""),
                description=s.get("description", ""),
                accessed_at=s.get("accessed_at", ""),
            )
            for s in data.get("sources", [])
        ]

        steps = [
            ResearchStep(
                step_id=step.get("step_id", ""),
                iteration=step.get("iteration", 0),
                question=step.get("question", ""),
                findings=step.get("findings", ""),
                confidence=step.get("confidence", 0.0),
                sources=[
                    Source(
                        url=s.get("url", ""),
                        title=s.get("title", ""),
                        description=s.get("description", ""),
                        accessed_at=s.get("accessed_at", ""),
                    )
                    for s in step.get("sources", [])
                ],
                timestamp=step.get("timestamp", ""),
            )
            for step in data.get("steps", [])
        ]

        return ResearchResult(
            workflow_id=data["workflow_id"],
            query=data["query"],
            status=data["status"],
            final_summary=data["final_summary"],
            total_iterations=data["total_iterations"],
            duration_seconds=data["duration_seconds"],
            steps=steps,
            sources=sources,
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "ResearchApiClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
