"""
Centralized tracing configuration for HEALTH-BRIDGE.

Provides:
- Opik initialization from environment variables
- TRACING_ENABLED gate (default: false for dev)
- No-op @track fallback when tracing is disabled
- configure_tracing() to be called at app startup
"""

import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

_tracing_initialized = False
_tracing_enabled = False


def configure_tracing():
    """Initialize Opik tracing from environment variables.

    Call this once at application startup (e.g. in main.py or app factory).

    Environment variables:
        TRACING_ENABLED: "true" to enable (default: "false")
        OPIK_API_KEY: Opik API key
        OPIK_PROJECT_NAME: Opik project name
        OPIK_WORKSPACE: Opik workspace name
    """
    global _tracing_initialized, _tracing_enabled

    if _tracing_initialized:
        return

    _tracing_enabled = os.getenv("TRACING_ENABLED", "false").lower() == "true"
    _tracing_initialized = True

    if not _tracing_enabled:
        logger.info("Tracing disabled (set TRACING_ENABLED=true to enable)")
        return

    api_key = os.getenv("OPIK_API_KEY")
    project = os.getenv("OPIK_PROJECT_NAME", "health-bridge")
    workspace = os.getenv("OPIK_WORKSPACE", "default")

    if not api_key:
        logger.warning("TRACING_ENABLED=true but OPIK_API_KEY not set; tracing disabled")
        _tracing_enabled = False
        return

    try:
        import opik
        opik.configure(
            api_key=api_key,
            project_name=project,
            workspace=workspace,
        )
        logger.info(f"Opik tracing initialized: project={project}, workspace={workspace}")
    except Exception as e:
        logger.warning(f"Failed to initialize Opik tracing: {e}")
        _tracing_enabled = False


def is_tracing_enabled() -> bool:
    """Check if tracing is currently enabled."""
    if not _tracing_initialized:
        configure_tracing()
    return _tracing_enabled


def tracked(name: str = None, tags: list = None):
    """Decorator that wraps a function with Opik @track when tracing is enabled.

    Falls back to a no-op when tracing is disabled, avoiding import errors
    or overhead.

    Args:
        name: Trace span name (defaults to function name)
        tags: Optional list of tags for filtering in the Opik dashboard

    Usage:
        @tracked(name="retrieve_guidelines", tags=["tool"])
        def retrieve_guidelines(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_tracing_enabled():
                try:
                    from opik import track
                    track_kwargs = {}
                    if name:
                        track_kwargs["name"] = name
                    if tags:
                        track_kwargs["tags"] = tags
                    decorated = track(**track_kwargs)(func) if track_kwargs else track(func)
                    return decorated(*args, **kwargs)
                except Exception:
                    pass
            return func(*args, **kwargs)
        return wrapper
    return decorator
