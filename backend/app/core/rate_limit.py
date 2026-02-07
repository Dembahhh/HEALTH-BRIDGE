"""
Rate limiting configuration for HEALTH-BRIDGE API.

Uses slowapi with in-memory storage by default.
When Redis is available, uses Redis-backed storage for multi-worker support.
"""

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)


def _get_user_or_ip(request: Request) -> str:
    """Rate limit key: use authenticated user ID if available, else IP."""
    # Check if auth already resolved a user (set by deps.py)
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        uid = user.get("uid")
        if uid:
            return f"user:{uid}"
    return get_remote_address(request)


def create_limiter() -> Limiter:
    """Create the rate limiter instance.

    Tries Redis first (for multi-worker), falls back to in-memory.
    """
    from app.config.settings import settings

    storage_uri = None
    try:
        if settings.REDIS_URL:
            # Test Redis connectivity before using it
            import redis
            r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            r.ping()
            storage_uri = settings.REDIS_URL
            logger.info("Rate limiter using Redis: %s", storage_uri)
    except Exception as e:
        logger.info("Redis unavailable, using in-memory rate limiter: %s", e)

    if storage_uri:
        try:
            return Limiter(
                key_func=_get_user_or_ip,
                storage_uri=storage_uri,
                default_limits=["200/minute"],
            )
        except Exception as e:
            logger.warning("Redis rate limiter failed, using in-memory: %s", e)

    logger.info("Rate limiter using in-memory storage")
    return Limiter(
        key_func=_get_user_or_ip,
        default_limits=["200/minute"],
    )


limiter = create_limiter()
