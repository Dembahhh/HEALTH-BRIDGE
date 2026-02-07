"""
Database Configuration

MongoDB connection and initialization using Motor and Beanie.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Global client reference
_client: AsyncIOMotorClient | None = None


async def init_db() -> None:
    """Initialize MongoDB connection and Beanie ODM."""
    global _client

    _client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        maxPoolSize=50,
        minPoolSize=5,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
    )

    # Import models here to avoid circular imports
    from app.models.user import User
    from app.models.profile import HealthProfile
    from app.models.plan import HabitPlan
    from app.models.chat import ChatSession, ChatMessage

    await init_beanie(
        database=_client[settings.MONGODB_DB_NAME],
        document_models=[
            User,
            HealthProfile,
            HabitPlan,
            ChatSession,
            ChatMessage,
        ],
    )


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        _client = None


def get_database():
    """Get database instance."""
    if _client is None:
        raise RuntimeError("Database not initialized")
    return _client[settings.MONGODB_DB_NAME]
