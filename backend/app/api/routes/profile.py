"""
Profile API Routes

Endpoints for health profile management.
"""

from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models.profile import HealthProfile, Constraints

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ConstraintsModel(BaseModel):
    """SDOH constraints."""
    exercise_safety: Optional[str] = None
    income_band: Optional[str] = None
    food_access: Optional[str] = None
    time_availability: Optional[str] = None
    additional_notes: Optional[str] = None


class ProfileResponse(BaseModel):
    """Health profile response."""
    photo_url: Optional[str] = None
    age_band: Optional[str] = None
    sex: Optional[str] = None
    family_history_hypertension: Optional[bool] = None
    family_history_diabetes: Optional[bool] = None
    smoking_status: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    bmi_category: Optional[str] = None
    activity_level: Optional[str] = None
    diet_pattern: Optional[str] = None
    risk_bands: Optional[dict] = None
    top_risk_factors: Optional[List[str]] = None
    constraints: Optional[ConstraintsModel] = None


class UpdateProfileRequest(BaseModel):
    """Request to update profile."""
    photo_url: Optional[str] = None
    age_band: Optional[str] = None
    sex: Optional[str] = None
    family_history_hypertension: Optional[bool] = None
    family_history_diabetes: Optional[bool] = None
    smoking_status: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    bmi_category: Optional[str] = None
    activity_level: Optional[str] = None
    diet_pattern: Optional[str] = None
    constraints: Optional[ConstraintsModel] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(current_user) -> str:
    if isinstance(current_user, dict):
        return current_user.get("uid")
    return getattr(current_user, "firebase_uid", str(current_user.id))


async def _get_or_create_profile(uid: str) -> HealthProfile:
    """Fetch existing profile or create a blank one."""
    profile = await HealthProfile.find_one(HealthProfile.user_id == uid)
    if not profile:
        profile = HealthProfile(user_id=uid)
        await profile.insert()
    return profile


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=ProfileResponse)
async def get_profile(current_user: CurrentUser):
    """Get current user's health profile."""
    uid = _uid(current_user)
    profile = await HealthProfile.find_one(HealthProfile.user_id == uid)

    if not profile:
        return ProfileResponse()

    return ProfileResponse(**profile.model_dump())


@router.put("", response_model=ProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: CurrentUser,
):
    """Update user's health profile."""
    uid = _uid(current_user)
    profile = await _get_or_create_profile(uid)

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    profile.update_timestamp()
    await profile.save()

    return ProfileResponse(**profile.model_dump())


@router.get("/constraints", response_model=ConstraintsModel)
async def get_constraints(current_user: CurrentUser):
    """Get user's SDOH constraints."""
    uid = _uid(current_user)
    profile = await HealthProfile.find_one(HealthProfile.user_id == uid)

    if not profile or not profile.constraints:
        return ConstraintsModel()

    return ConstraintsModel(**profile.constraints.model_dump())


@router.put("/constraints", response_model=ConstraintsModel)
async def update_constraints(
    constraints: ConstraintsModel,
    current_user: CurrentUser,
):
    """Update user's SDOH constraints."""
    uid = _uid(current_user)
    profile = await _get_or_create_profile(uid)

    profile.constraints = Constraints(**constraints.model_dump())
    profile.update_timestamp()
    await profile.save()

    return ConstraintsModel(**profile.constraints.model_dump())
