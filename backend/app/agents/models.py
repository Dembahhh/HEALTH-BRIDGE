import json
import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


def strip_json_comments(json_str: str) -> str:
    """
    Remove inline comments from JSON strings that LLMs sometimes add.
    Handles both // comments and trailing comments after values.

    Example:
        '{"age": 23, // comment here\n"sex": "female"}'
        -> '{"age": 23,\n"sex": "female"}'
    """
    if not isinstance(json_str, str):
        return json_str

    # Remove // comments
    json_str = re.sub(r'\s*//[^\n]*', '', json_str)
    # Remove /* */ comments
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

    return json_str


# --- Core Models ---

class Profile(BaseModel):
    """User health profile collected during intake."""
    age: int = Field(..., description="Age of the user")
    sex: Literal["male", "female", "other", "unknown"] = Field(..., description="Sex of the user")
    weight_category: str = Field(..., description="Self-reported weight category or BMI band")
    activity_level: Literal["sedentary", "light", "moderate", "active", "unknown"] = Field(..., description="General activity level")
    diet_pattern: str = Field(..., description="Brief description of typical diet")
    family_history: List[str] = Field(default_factory=list, description="List of relevant family conditions (e.g. hypertension)")
    smoking: bool = Field(False, description="Does the user smoke?")
    alcohol: str = Field(..., description="Alcohol consumption habits")

    @model_validator(mode="before")
    @classmethod
    def strip_comments(cls, data):
        """Strip JSON comments if the LLM included them."""
        if isinstance(data, str):
            data = strip_json_comments(data)
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass  # Let pydantic handle the error
        return data

class RiskAssessment(BaseModel):
    """Risk analysis output from the Risk & Guideline Agent."""
    hypertension_risk: Literal["low", "moderate", "high"] = Field(..., description="Estimated risk band for hypertension")
    diabetes_risk: Literal["low", "moderate", "high"] = Field(..., description="Estimated risk band for type 2 diabetes")
    key_drivers: List[str] = Field(..., description="List of factors contributing to the risk")
    explanation: str = Field(..., description="User-friendly explanation of the risk profile")

class Constraints(BaseModel):
    """SDOH and environmental constraints."""
    exercise_safety: str = Field(..., description="Is it safe to exercise outdoors? e.g. 'unsafe_at_night'")
    food_access: str = Field(..., description="Access to fresh food vs processed food")
    time_constraints: str = Field(..., description="Work schedule or caregiving duties")
    financial_band: str = Field(..., description="Rough income/spending power context")

class Habit(BaseModel):
    """A single habit recommendation."""
    action: str = Field(..., description="The specific action to take (e.g. 'Walk 10 mins')")
    frequency: str = Field(..., description="How often to do it (e.g. '3x per week')")
    trigger: str = Field(..., description="When to do it (e.g. 'After dinner')")
    rationale: str = Field(..., description="Why this habit helps")

class HabitPlan(BaseModel):
    """The 4-week habit plan."""
    duration_weeks: int = Field(4, description="Duration of the plan in weeks")
    focus_areas: List[str] = Field(..., description="Main goals (e.g. 'Reduce salt', 'Increase movement')")
    habits: List[Habit] = Field(..., description="List of small habits to start")
    motivational_message: str = Field(..., description="Encouraging closing message")

class SafetyReview(BaseModel):
    """Output from the Safety Agent."""
    is_safe: bool = Field(..., description="Is the content safe to show the user?")
    flagged_issues: List[str] = Field(default_factory=list, description="List of safety violations if any")
    revised_response: Optional[str] = Field(None, description="Rewritten response if edits were needed")

    @field_validator("revised_response", mode="before")
    @classmethod
    def coerce_to_str(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        return v
