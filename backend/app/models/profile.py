"""
Health Profile Model

MongoDB document model for user health profiles and SDOH constraints.
"""

from datetime import datetime
from typing import Optional, List
from beanie import Document, Indexed
from pydantic import Field, BaseModel


class Constraints(BaseModel):
    """Social Determinants of Health (SDOH) constraints."""

    exercise_safety: Optional[str] = None  # safe, unsafe_at_night, unsafe
    income_band: Optional[str] = None  # low, moderate, high
    food_access: Optional[str] = None  # limited_fresh, moderate, good
    time_availability: Optional[str] = None  # limited, moderate, flexible
    additional_notes: Optional[str] = None


class ConversationEntry(BaseModel):
    """A single conversation exchange stored on the profile for cross-session memory."""

    user_message: str  # truncated to 200 chars on append
    assistant_message: str  # truncated to 300 chars on append
    question_type: str = "general_health"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthProfile(Document):
    """User health profile document model."""

    user_id: Indexed(str)  # Reference to User.firebase_uid
    photo_url: Optional[str] = None  # Profile picture URL

    # Demographics
    age_band: Optional[str] = None  # 18-29, 30-39, 40-49, 50-59, 60+
    sex: Optional[str] = None  # male, female

    # Health history
    family_history_hypertension: Optional[bool] = None
    family_history_diabetes: Optional[bool] = None
    smoking_status: Optional[str] = None  # never, former, current
    alcohol_consumption: Optional[str] = None  # none, occasional, regular

    # Physical metrics
    bmi_category: Optional[str] = None  # underweight, normal, overweight, obese

    # Lifestyle
    activity_level: Optional[str] = None  # sedentary, light, moderate, active
    diet_pattern: Optional[str] = None  # high_salt, high_sugar, mixed, healthy

    # Risk assessment (computed by Risk Agent)
    risk_bands: Optional[dict] = None  # {"hypertension": "moderate", "diabetes": "low"}
    top_risk_factors: Optional[List[str]] = None

    # SDOH Constraints
    constraints: Constraints = Field(default_factory=Constraints)

    # Cross-session conversation history (ring buffer, max 20 entries)
    conversation_history: List[ConversationEntry] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "health_profiles"

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def append_conversation(
        self,
        user_msg: str,
        assistant_msg: str,
        question_type: str = "general_health",
    ):
        """Append a conversation entry, enforcing a 20-entry ring buffer cap."""
        entry = ConversationEntry(
            user_message=user_msg[:200],
            assistant_message=assistant_msg[:300],
            question_type=question_type,
        )
        self.conversation_history.append(entry)
        # Keep only the most recent 20 entries
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        self.update_timestamp()

    def get_history_for_llm(self, max_entries: int = 10) -> List[dict]:
        """Return recent conversation history as a list of role/content dicts for LLM context."""
        recent = self.conversation_history[-max_entries:]
        messages = []
        for entry in recent:
            messages.append({"role": "user", "content": entry.user_message})
            messages.append({"role": "assistant", "content": entry.assistant_message})
        return messages
