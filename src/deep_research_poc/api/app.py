"""FastAPI application factory and configuration.

This module provides the FastAPI application factory following best practices
for application structure, dependency injection, and lifecycle management.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from deep_research_poc.api.routes import health_router, research_router
from deep_research_poc.config import get_settings
from deep_research_poc.logging_config import configure_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown tasks like initializing connections
    and cleaning up resources.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info(
        "starting_api_server",
        temporal_address=settings.temporal_address,
        task_queue=settings.temporal_task_queue,
    )

    yield

    # Cleanup
    if hasattr(app.state, "temporal_client"):
        logger.info("closing_temporal_client")
        # Note: Temporal client doesn't have an explicit close method
        # but we can clear the reference
        del app.state.temporal_client

    logger.info("api_server_shutdown")


def create_app(
    title: str = "Deep Research API",
    description: str | None = None,
    **kwargs: Any,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        title: API title for OpenAPI docs
        description: API description for OpenAPI docs
        **kwargs: Additional FastAPI configuration

    Returns:
        Configured FastAPI application instance
    """
    if description is None:
        description = """
        Deep Research API provides AI-powered research capabilities using
        a multi-agent architecture with Temporal workflow orchestration.

        ## Features

        - **Async Research**: Start research workflows and check status later
        - **Sync Research**: Run research and wait for results
        - **Multi-Agent Architecture**: Planning, research, validation, and critique agents
        - **Source Citations**: All research includes proper source attribution

        ## Research Depths

        - `quick`: Fast, single-iteration research
        - `standard`: Balanced depth with 3 iterations (default)
        - `deep`: Comprehensive research with 5+ iterations
        """

    app = FastAPI(
        title=title,
        description=description,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        **kwargs,
    )

    # Add CORS middleware for browser access
    # Note: Configure allow_origins appropriately for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure from settings for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(research_router, prefix="/api/v1")

    return app


# Default application instance for uvicorn
app = create_app()
