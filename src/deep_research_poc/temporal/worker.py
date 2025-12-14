"""Temporal worker for research workflows.

This module runs the Temporal worker that executes research workflows
and activities. It handles graceful shutdown and logging.

Usage:
    python -m deep_research_poc.temporal.worker
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Any

import structlog
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from deep_research_poc.config import get_settings
from deep_research_poc.logging_config import configure_logging
from deep_research_poc.temporal.activities import (
    conduct_research_activity,
    create_research_plan_activity,
    expand_query_activity,
    synthesize_findings_activity,
    validate_research_activity,
)
from deep_research_poc.temporal.workflows import DeepResearchWorkflow

logger = structlog.get_logger()


async def run_worker() -> None:
    """Run the Temporal worker.
    
    Connects to Temporal and runs until interrupted.
    Handles graceful shutdown on SIGINT/SIGTERM.
    """
    settings = get_settings()

    logger.info(
        "starting_worker",
        temporal_address=settings.temporal_address,
        task_queue=settings.temporal_task_queue,
        namespace=settings.temporal_namespace,
    )

    # Connect to Temporal with Pydantic data converter
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=pydantic_data_converter,
    )

    # Create worker with workflows and activities
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[DeepResearchWorkflow],
        activities=[
            conduct_research_activity,
            synthesize_findings_activity,
            create_research_plan_activity,
            validate_research_activity,
            expand_query_activity,
        ],
    )

    logger.info(
        "worker_started",
        task_queue=settings.temporal_task_queue,
        workflows=["DeepResearchWorkflow"],
        activities=[
            "conduct_research_activity",
            "synthesize_findings_activity",
            "create_research_plan_activity",
            "validate_research_activity",
            "expand_query_activity",
        ],
    )

    # Set up graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig: Any, frame: Any) -> None:
        logger.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run worker until shutdown
    try:
        async with worker:
            print("🚀 Worker running. Press Ctrl+C to stop.")
            await shutdown_event.wait()
    finally:
        logger.info("worker_stopped")


async def main() -> None:
    """Main entry point."""
    settings = get_settings()
    configure_logging(settings.log_level)
    await run_worker()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("worker_interrupted")
        sys.exit(0)
