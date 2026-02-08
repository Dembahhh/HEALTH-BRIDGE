"""
Chat Models

MongoDB document models for chat sessions and messages.
"""

from datetime import datetime
from typing import Optional, List
from beanie import Document, Indexed
from pydantic import Field


class ChatMessage(Document):
    """Individual chat message."""

    session_id: Indexed(str)
    role: str  # user, assistant
    content: str

    # Agent metadata
    agent_name: Optional[str] = None  # Which agent generated this
    tool_calls: Optional[List[dict]] = None  # Tool calls made

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chat_messages"


class ChatSession(Document):
    """Chat session document model."""

    user_id: Indexed(str)  # Reference to User.firebase_uid
    session_id: Indexed(str, unique=True)  # Unique session identifier

    # Session metadata
    session_type: str = "general"  # intake, follow_up, general
    is_active: bool = True

    # Context
    context_summary: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chat_sessions"

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
