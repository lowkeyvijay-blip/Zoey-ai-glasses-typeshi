"""V2.0 Lifecycle manager.

Manages startup hooks, shutdown hooks, camera initialization,
pipeline initialization, graceful cleanup, and health/status
reporting.

The application must not crash merely because a camera or
MediaPipe model is unavailable during import.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from backend.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Application lifecycle manager.

    Tracks startup/shutdown hooks and provides health/status
    reporting. Ensures graceful cleanup on shutdown.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._started_at: Optional[float] = None
        self._running = False
        self._components: Dict[str, str] = {}

    def on_startup(self, hook: Callable) -> None:
        """Register a startup hook."""
        self._startup_hooks.append(hook)

    def on_shutdown(self, hook: Callable) -> None:
        """Register a shutdown hook."""
        self._shutdown_hooks.append(hook)

    def register_component(self, name: str, status: str = "registered") -> None:
        """Register a component for health tracking."""
        self._components[name] = status

    def update_component(self, name: str, status: str) -> None:
        """Update component status."""
        self._components[name] = status

    async def startup(self) -> None:
        """Execute startup hooks."""
        self._started_at = time.time()
        self._running = True
        logger.info("Zoey Spatial V2.0 starting up")

        for hook in self._startup_hooks:
            try:
                result = hook()
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                logger.exception("Startup hook failed: %s", hook.__name__)

        logger.info("Startup complete")

    async def shutdown(self) -> None:
        """Execute shutdown hooks in reverse order."""
        logger.info("Shutting down Zoey Spatial")
        self._running = False

        for hook in reversed(self._shutdown_hooks):
            try:
                result = hook()
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                logger.exception("Shutdown hook failed: %s", hook.__name__)

        logger.info("Shutdown complete")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def health(self) -> Dict[str, Any]:
        """Report application health status."""
        return {
            "status": "running" if self._running else "stopped",
            "uptime_seconds": round(self.uptime, 1),
            "components": dict(self._components),
            "version": "2.0",
        }
