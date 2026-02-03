"""
Chat Models

MongoDB document models for chat sessions and messages.
"""

from datetime import datetime
from typing import Optional, List, Literal
from beanie import Document, Indexed
from pydantic import Field


class ChatMessage(Document):
    """Individual chat message."""

    session_id: Indexed(str)
    user_id: Indexed(str)

    role: Literal["user", "assistant", "system"] = "user"
    content: str

    # Optional metadata
    agent_name: Optional[str] = None  # Which agent responded
    tokens_used: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chat_messages"


class ChatSession(Document):
    """Chat session containing multiple messages."""

    user_id: Indexed(str)  # Reference to User.firebase_uid

    session_type: Literal["intake", "follow_up", "general"] = "general"
    status: Literal["active", "completed", "abandoned"] = "active"

    # Summary for context
    summary: Optional[str] = None

    # Generated outputs (references)
    habit_plan_id: Optional[str] = None  # Reference to HabitPlan if generated
    risk_assessment: Optional[dict] = None  # Inline risk data

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chat_sessions"

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
