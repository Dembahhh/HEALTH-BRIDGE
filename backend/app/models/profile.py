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

    exercise_safety: str = "safe"  # safe, unsafe_at_night, unsafe
    income_band: str = "moderate"  # low, moderate, high
    food_access: str = "good"  # limited_fresh, moderate, good
    time_availability: str = "moderate"  # limited, moderate, flexible
    additional_notes: Optional[str] = None


class HealthProfile(Document):
    """User health profile document model."""

    user_id: Indexed(str)  # Reference to User.firebase_uid
    photo_url: Optional[str] = None  # Profile picture URL

    # Demographics
    age_band: Optional[str] = None  # 18-29, 30-39, 40-49, 50-59, 60+
    sex: Optional[str] = None  # male, female

    # Health history
    family_history_hypertension: bool = False
    family_history_diabetes: bool = False
    smoking_status: str = "never"  # never, former, current
    alcohol_consumption: str = "none"  # none, occasional, regular

    # Physical metrics
    bmi_category: str = "normal"  # underweight, normal, overweight, obese

    # Lifestyle
    activity_level: str = "sedentary"  # sedentary, light, moderate, active
    diet_pattern: str = "mixed"  # high_salt, high_sugar, mixed, healthy

    # Risk assessment (computed by Risk Agent)
    risk_bands: Optional[dict] = None  # {"hypertension": "moderate", "diabetes": "low"}
    top_risk_factors: Optional[List[str]] = None

    # SDOH Constraints
    constraints: Constraints = Field(default_factory=Constraints)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "health_profiles"

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
