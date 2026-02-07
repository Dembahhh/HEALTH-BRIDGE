"""
Plans API Routes

Endpoints for habit plan management.
"""

from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import CurrentUser

router = APIRouter()


# Request/Response Models
class HabitModel(BaseModel):
    """Individual habit."""
    title: str
    description: str
    frequency: str  
    category: str  
    difficulty: str = "easy"


class PlanResponse(BaseModel):
    """Habit plan response."""
    plan_id: Optional[str] = None
    week_number: int = 1
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    habits: List[HabitModel] = []
    status: str = "active"


class FeedbackRequest(BaseModel):
    """Submit feedback on plan adherence."""
    plan_id: str
    adherence_notes: Optional[str] = None
    obstacles: Optional[List[str]] = None
    successes: Optional[List[str]] = None


class FeedbackResponse(BaseModel):
    """Feedback submission response."""
    status: str
    plan_id: str
    message: str


# Endpoints
@router.get("/current", response_model=PlanResponse)
async def get_current_plan(current_user: CurrentUser):
    """Get user's current active habit plan."""
    # TODO: Retrieve current plan from database (Phase 7)
    return PlanResponse()


@router.get("/history")
async def get_plan_history(current_user: CurrentUser):
    """Get user's plan history."""
    # TODO: Retrieve plan history from database (Phase 7)
    return {"plans": []}


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: CurrentUser,
):
    """
    Submit feedback on plan adherence.

    This feedback is used by the Habit Coach agent to adapt future plans.
    """
    # TODO: Store feedback and trigger plan adaptation (Phase 6/7)
    return FeedbackResponse(
        status="received",
        plan_id=feedback.plan_id,
        message="Thank you for your feedback! We'll use this to improve your next plan.",
    )
