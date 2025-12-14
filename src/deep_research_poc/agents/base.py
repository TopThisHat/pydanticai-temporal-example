"""Base class for specialized agents.

This module provides the abstract base class that all specialized
agents inherit from, ensuring consistent interface and behavior.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

import structlog

from deep_research_poc.config import Settings, get_settings

logger = structlog.get_logger()

# Type variable for agent output types
T = TypeVar("T")


class BaseSpecializedAgent(ABC, Generic[T]):
    """Abstract base class for specialized agents.
    
    All specialized agents (Planning, Validation, Critique, etc.) inherit
    from this class to ensure consistent interface and logging.
    
    Attributes:
        agent: The pydantic-ai agent instance
        settings: Application settings
        agent_name: Human-readable name for logging
    """

    def __init__(
        self,
        agent: Any,
        settings: Settings | None = None,
        agent_name: str = "specialized_agent",
    ) -> None:
        """Initialize the specialized agent.
        
        Args:
            agent: Pydantic-ai agent for this specialized task
            settings: Optional settings (uses defaults if not provided)
            agent_name: Name for logging purposes
        """
        self.agent = agent
        self.settings = settings or get_settings()
        self.agent_name = agent_name
        
        logger.info(
            f"{agent_name}_initialized",
            model=self.settings.openai_model,
        )

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> T:
        """Execute the agent's primary task.
        
        Subclasses must implement this method to define their
        specific behavior.
        
        Returns:
            The agent's output of type T
        """
        pass

    def _log_start(self, **context: Any) -> structlog.BoundLogger:
        """Log the start of agent execution with context.
        
        Args:
            **context: Additional context to log
            
        Returns:
            Bound logger for continued logging
        """
        log = logger.bind(agent=self.agent_name, **context)
        log.info(f"{self.agent_name}_started")
        return log

    def _log_success(self, log: structlog.BoundLogger, **context: Any) -> None:
        """Log successful completion.
        
        Args:
            log: Bound logger from _log_start
            **context: Additional context to log
        """
        log.info(f"{self.agent_name}_completed", **context)

    def _log_error(
        self,
        log: structlog.BoundLogger,
        error: Exception,
        **context: Any,
    ) -> None:
        """Log an error.
        
        Args:
            log: Bound logger from _log_start
            error: The exception that occurred
            **context: Additional context to log
        """
        log.error(
            f"{self.agent_name}_failed",
            error=str(error),
            exc_info=True,
            **context,
        )
