"""Entry point for running the FastAPI server.

Usage:
    python -m deep_research_poc.api

This starts the uvicorn server with the FastAPI application.
"""

from __future__ import annotations

import uvicorn

from deep_research_poc.config import get_settings


def main() -> None:
    """Run the FastAPI server."""
    settings = get_settings()

    uvicorn.run(
        "deep_research_poc.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
