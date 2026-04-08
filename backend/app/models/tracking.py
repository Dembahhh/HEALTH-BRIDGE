"""
Tracking Log Model

MongoDB document model for health tracking logs (BP, glucose, medication).
"""

from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field, model_validator
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.models.screening import Classification

# Module-level type aliases
LogType         = Literal["bp", "glucose", "medication"]
ActionType      = Literal["diet", "exercise", "medication", "monitoring", "referral", "glucose", "bp"]
GlucoseUnit     = Literal["mmol_l", "mg_dl"]
GlucoseTestType = Literal["random", "fasting"]


class MedicationEntry(BaseModel):
    """A single medication taken/skipped record."""
    name: str
    taken: bool = False


class NudgeData(BaseModel):
    """AI-generated nudge returned by the Habit Coach agent."""
    text: str
    action_type: ActionType = "monitoring"
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_action_type(cls, values):
        allowed = {"diet", "exercise", "medication", "monitoring", "referral", "glucose", "bp"}
        if isinstance(values, dict):
            if values.get("action_type") not in allowed:
                values["action_type"] = "monitoring"  # safe fallback
        return values
class TrackingLog(Document):
    """Health tracking log — one check-in entry per document."""

    #Identity
    user_id: Annotated[str, Indexed()]
    patient_id: Annotated[str, Indexed()]
    log_type: LogType

    # BP fields
    systolic: Optional[int] = Field(default=None, ge=40, le=300)
    diastolic: Optional[int] = Field(default=None, ge=20, le=200)
    bp_classification: Optional[Classification] = None

    # Glucose fields
    glucose_value: Optional[float] = Field(default=None, ge=0.0)
    glucose_unit: Optional[GlucoseUnit] = None
    glucose_test_type: Optional[GlucoseTestType] = None
    glucose_classification: Optional[Classification] = None

    # Medication fields
    medications: Optional[list[MedicationEntry]] = None

    #Common fields
    mood: Optional[Literal["good", "okay", "bad"]] = None
    notes: Optional[str] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # AI response 
    nudge: Optional[NudgeData] = None

    @model_validator(mode="after")
    def _validate_log_type_fields(self) -> "TrackingLog":
        """Enforce required fields are present for the given log_type."""
        if self.log_type == "bp":
            if self.systolic is None or self.diastolic is None:
                raise ValueError("systolic and diastolic are required for bp logs")
        elif self.log_type == "glucose":
            if self.glucose_value is None or self.glucose_unit is None:
                raise ValueError("glucose_value and glucose_unit are required for glucose logs")
        elif self.log_type == "medication":
            if not self.medications:
                raise ValueError("medications list is required for medication logs")
        return self

    class Settings:
        name = "tracking_logs"
        indexes = [
            IndexModel(
                [("user_id", DESCENDING), ("timestamp", DESCENDING)],
                name="user_timestamp_desc",
            ),
            IndexModel(
                [("patient_id", DESCENDING), ("timestamp", DESCENDING)],
                name="patient_timestamp_desc",
            ),
            IndexModel(
                [("user_id", DESCENDING), ("log_type", ASCENDING), ("timestamp", DESCENDING)],
                name="user_logtype_timestamp_desc",
            ),
            IndexModel(
                [("patient_id", DESCENDING), ("log_type", ASCENDING), ("timestamp", DESCENDING)],
                name="patient_logtype_timestamp_desc",
            ),
        ]