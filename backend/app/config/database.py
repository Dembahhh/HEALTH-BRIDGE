"""
Database Configuration

MongoDB connection and initialization using Motor and Beanie.
Includes retry logic with exponential backoff so the backend
waits for MongoDB to be ready rather than failing immediately
on container startup.
"""
from __future__ import annotations

import asyncio
import logging

import certifi
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError  
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Global client reference
_client: AsyncIOMotorClient | None = None


# Retry helper 

async def _connect_with_retry(
    url: str,
    max_retries: int = 5,
    base_delay: float = 2.0,
) -> AsyncIOMotorClient:  
    """Attempt to connect to MongoDB with linear backoff."""
    last_error: Exception | None = None  

    for attempt in range(1, max_retries + 1):  
        try:
            client = AsyncIOMotorClient(
                url,
                maxPoolSize=50,
                minPoolSize=5,
                serverSelectionTimeoutMS=5_000,
                connectTimeoutMS=10_000,
                tlsCAFile=certifi.where(),
            )
            await client.admin.command("ping")
            logger.info(
                "MongoDB connected on attempt %d/%d", attempt, max_retries  
            )
            return client

        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:  
            last_error = exc
            if attempt == max_retries:
                logger.error(
                    "MongoDB unavailable after %d attempts — giving up.", max_retries  
                )
                raise  

            delay = base_delay * attempt 
            logger.warning(
                "MongoDB not ready (attempt %d/%d), retrying in %.0f s — %s",
                attempt,
                max_retries,
                delay,
                exc,
            )
            await asyncio.sleep(delay)

    raise last_error  # type: ignore[misc]  


#Public interface 

async def init_db() -> None:
    """Initialize MongoDB connection and Beanie ODM."""
    global _client

    _client = await _connect_with_retry(url=settings.MONGODB_URL)  

    from app.models.chat import ChatSession, ChatMessage, MessageFeedback
    from app.models.patient import Patient
    from app.models.plan import HabitPlan
    from app.models.profile import HealthProfile
    from app.models.screening import ScreeningSession
    from app.models.tracking import TrackingLog
    from app.models.user import User

    await init_beanie(
        database=_client[settings.MONGODB_DB_NAME],
        document_models=[
            User,
            HealthProfile,
            HabitPlan,
            ChatSession,
            ChatMessage,
            MessageFeedback,
            TrackingLog,
            ScreeningSession,
            Patient,
        ],
    )
    logger.info("Beanie ODM initialised — database: %s", settings.MONGODB_DB_NAME)


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")


def get_database():
    """Get database instance."""
    if _client is None:
        raise RuntimeError(
            "Database not initialised. Ensure init_db() is awaited at startup."
        )
    return _client[settings.MONGODB_DB_NAME]