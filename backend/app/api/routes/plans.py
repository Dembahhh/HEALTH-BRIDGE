"""
Plans API Routes

Endpoints for habit plan management.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import CurrentUser
from app.models.plan import HabitPlan, Habit

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(current_user) -> str:
    if isinstance(current_user, dict):
        return current_user.get("uid")
    return getattr(current_user, "firebase_uid", str(current_user.id))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/current", response_model=PlanResponse)
async def get_current_plan(current_user: CurrentUser):
    """Get user's current active habit plan."""
    uid = _uid(current_user)

    plan = await HabitPlan.find_one(
        HabitPlan.user_id == uid,
        HabitPlan.status == "active",
    )

    if not plan:
        return PlanResponse()

    return PlanResponse(
        plan_id=str(plan.id),
        week_number=plan.week_number,
        start_date=plan.start_date,
        end_date=plan.end_date,
        habits=[
            HabitModel(
                title=h.title,
                description=h.description,
                frequency=h.frequency,
                category=h.category,
                difficulty=h.difficulty,
            )
            for h in plan.habits
        ],
        status=plan.status,
    )


@router.get("/history")
async def get_plan_history(current_user: CurrentUser):
    """Get user's plan history."""
    uid = _uid(current_user)

    plans = await HabitPlan.find(
        HabitPlan.user_id == uid
    ).sort("-created_at").to_list()

    return {
        "plans": [
            PlanResponse(
                plan_id=str(p.id),
                week_number=p.week_number,
                start_date=p.start_date,
                end_date=p.end_date,
                habits=[
                    HabitModel(
                        title=h.title,
                        description=h.description,
                        frequency=h.frequency,
                        category=h.category,
                        difficulty=h.difficulty,
                    )
                    for h in p.habits
                ],
                status=p.status,
            ).model_dump()
            for p in plans
        ]
    }


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: CurrentUser,
):
    """
    Submit feedback on plan adherence.

    This feedback is used by the Habit Coach agent to adapt future plans.
    """
    uid = _uid(current_user)

    # Find the plan by id
    from beanie import PydanticObjectId

    try:
        plan = await HabitPlan.get(PydanticObjectId(feedback.plan_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not plan or plan.user_id != uid:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Store the feedback
    if feedback.adherence_notes:
        plan.adherence_notes = feedback.adherence_notes
    if feedback.obstacles:
        plan.obstacles_reported = feedback.obstacles
    if feedback.successes:
        plan.successes_reported = feedback.successes

    plan.update_timestamp()
    await plan.save()

    return FeedbackResponse(
        status="received",
        plan_id=feedback.plan_id,
        message="Thank you for your feedback! We'll use this to improve your next plan.",
    )
