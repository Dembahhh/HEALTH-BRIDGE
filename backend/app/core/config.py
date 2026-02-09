"""
Centralized configuration gating for HEALTH-BRIDGE.

Provides conditional Opik tracing support:
- Set OPIK_ENABLED=true and OPIK_API_KEY to enable tracing.
- When disabled, `tracked()` is a transparent no-op decorator.
"""

import logging
import os
from functools import wraps

logger = logging.getLogger(__name__)

_tracing_enabled: bool = False
_tracing_configured: bool = False


def configure_tracing():
    """Initialize Opik tracing if OPIK_ENABLED=true and the package is installed."""
    global _tracing_enabled, _tracing_configured

    if _tracing_configured:
        return

    _tracing_configured = True
    enabled = os.getenv("OPIK_ENABLED", "false").lower() == "true"

    if not enabled:
        logger.info("Opik tracing disabled (OPIK_ENABLED != true)")
        return

    try:
        import opik
        api_key = os.getenv("OPIK_API_KEY", "")
        project = os.getenv("OPIK_PROJECT", "health-bridge")
        workspace = os.getenv("OPIK_WORKSPACE", "default")

        opik.configure(
            api_key=api_key,
            project_name=project,
            workspace=workspace,
            use_local=not api_key,
        )
        _tracing_enabled = True
        logger.info("Opik tracing enabled: project=%s workspace=%s", project, workspace)
    except ImportError:
        logger.warning("Opik package not installed — tracing disabled")
    except Exception as e:
        logger.warning("Opik configuration failed: %s — tracing disabled", e)


def is_tracing_enabled() -> bool:
    """Return whether Opik tracing is active."""
    return _tracing_enabled


def tracked(name: str = None, tags: list = None):
    """Decorator that wraps a function with Opik tracking when enabled.

    Falls back to a transparent no-op when tracing is disabled or unavailable.
    """
    def decorator(func):
        if _tracing_enabled:
            try:
                from opik import track
                return track(name=name or func.__name__, tags=tags or [])(func)
            except Exception:
                pass

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
