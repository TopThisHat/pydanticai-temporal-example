"""FastAPI dependency injection providers.

This module provides dependency injection for the API, following FastAPI best practices.
Dependencies are properly typed and cached where appropriate.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends, Request
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from deep_research_poc.config import Settings, get_settings

logger = structlog.get_logger()


def get_settings_dep() -> Settings:
    """Dependency to provide application settings.

    Uses the cached settings from config module.

    Returns:
        Application settings instance
    """
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


async def get_temporal_client(
    request: Request,
) -> AsyncGenerator[Client, None]:
    """Dependency to provide a Temporal client.

    The client is stored in app state and reused across requests.
    This avoids creating new connections for each request.

    Args:
        request: FastAPI request object

    Yields:
        Temporal client instance
    """
    # Get or create client from app state
    if not hasattr(request.app.state, "temporal_client"):
        settings = get_settings()
        logger.info(
            "creating_temporal_client",
            address=settings.temporal_address,
            namespace=settings.temporal_namespace,
        )
        request.app.state.temporal_client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            data_converter=pydantic_data_converter,
        )

    yield request.app.state.temporal_client


TemporalClientDep = Annotated[Client, Depends(get_temporal_client)]


async def check_temporal_connection(settings: SettingsDep) -> bool:
    """Check if Temporal server is reachable.

    Args:
        settings: Application settings

    Returns:
        True if Temporal is reachable, False otherwise
    """
    try:
        client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            data_converter=pydantic_data_converter,
        )
        # Simple check - just connecting is enough
        await client.service_client.check_health()
        return True
    except Exception as e:
        logger.warning("temporal_health_check_failed", error=str(e))
        return False


TemporalHealthDep = Annotated[bool, Depends(check_temporal_connection)]
