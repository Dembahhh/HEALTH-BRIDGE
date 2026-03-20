"""
Tracking API Routes

Endpoints for logging health data (BP, glucose, medication) and retrieving history.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models.tracking import TrackingLog, MedicationEntry, NudgeData
from app.core.classifiers.bp import classify_bp
from app.core.classifiers.glucose import classify_glucose
from app.services.nudges import generate_tracking_nudge  # Phase 1: Nudges

router = APIRouter()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class TrackingLogRequest(BaseModel):
    """Request payload for logging a check-in."""
    log_type: str  # "bp" | "glucose" | "medication"

    # BP
    systolic: Optional[int] = None
    diastolic: Optional[int] = None

    # Glucose
    glucose_value: Optional[float] = None
    glucose_unit: Optional[str] = "mmol_l"
    glucose_test_type: Optional[str] = None  # "random" | "fasting"

    # Medication
    medications: Optional[List[MedicationEntry]] = None

    # Common
    mood: Optional[str] = None
    notes: Optional[str] = None


class TrackingLogResponse(BaseModel):
    """Response payload for a check-in (matches TrackingLog schema visually)."""
    id: str
    log_type: str
    timestamp: datetime
    
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    bp_classification: Optional[dict] = None
    
    glucose_value: Optional[float] = None
    glucose_unit: Optional[str] = None
    glucose_test_type: Optional[str] = None
    glucose_classification: Optional[dict] = None
    
    medications: Optional[List[MedicationEntry]] = None
    
    mood: Optional[str] = None
    notes: Optional[str] = None
    nudge: Optional[NudgeData] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(current_user) -> str:
    """Extract Firebase UID safely from the user object/dict."""
    if isinstance(current_user, dict):
        return current_user.get("uid", "")
    return getattr(current_user, "firebase_uid", str(current_user.id))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/log", response_model=TrackingLogResponse)
async def log_tracking_entry(
    request: TrackingLogRequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    """
    Log a new health check-in.
    
    Runs the appropriate classifier based on `log_type` (bp or glucose).
    Saves the log to MongoDB and triggers Habit Coach nudge generation asynchronously.
    """
    uid = _uid(current_user)
    
    log_entry = TrackingLog(
        user_id=uid,
        log_type=request.log_type,
        mood=request.mood,
        notes=request.notes,
        timestamp=datetime.utcnow(),
    )

    # 1. Process BP
    if request.log_type == "bp":
        if request.systolic is None or request.diastolic is None:
            raise HTTPException(status_code=400, detail="systolic and diastolic are required for BP logs")
        
        try:
            classification = classify_bp(request.systolic, request.diastolic)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        log_entry.systolic = request.systolic
        log_entry.diastolic = request.diastolic
        log_entry.bp_classification = classification

    # 2. Process Glucose
    elif request.log_type == "glucose":
        if request.glucose_value is None or request.glucose_test_type is None:
            raise HTTPException(status_code=400, detail="glucose_value and glucose_test_type are required for glucose logs")
            
        unit = request.glucose_unit or "mmol_l"
        if unit not in ("mmol_l", "mg_dl"):
            raise HTTPException(status_code=400, detail="glucose_unit must be 'mmol_l' or 'mg_dl'")
            
        try:
            test_type_literal = "random" if request.glucose_test_type == "random" else "fasting"
            if request.glucose_test_type not in ("random", "fasting"):
                raise ValueError("test_type must be 'random' or 'fasting'")
                
            unit_literal = "mmol_l" if unit == "mmol_l" else "mg_dl"
            
            classification = classify_glucose(
                request.glucose_value, 
                test_type_literal, 
                unit_literal
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        log_entry.glucose_value = request.glucose_value
        log_entry.glucose_test_type = request.glucose_test_type
        log_entry.glucose_unit = unit
        log_entry.glucose_classification = classification

    # 3. Process Medication
    elif request.log_type == "medication":
        if request.medications is None:
            raise HTTPException(status_code=400, detail="medications list is required for medication logs")
        log_entry.medications = request.medications
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid log_type: {request.log_type}")

    # Save to MongoDB
    await log_entry.insert()

    # Process AI Nudge asynchronously so the check-in is instant
    background_tasks.add_task(generate_tracking_nudge, str(log_entry.id), uid)
    
    # Format response
    response_data = log_entry.model_dump()
    response_data["id"] = str(log_entry.id)
    return TrackingLogResponse(**response_data)


@router.get("/history", response_model=List[TrackingLogResponse])
async def get_tracking_history(
    current_user: CurrentUser,
    type: Optional[str] = Query(None, description="Filter by log_type (bp, glucose, medication)"),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Get user's tracking history, descending by timestamp.
    """
    uid = _uid(current_user)
    
    query = {"user_id": uid}
    if type:
        query["log_type"] = type
        
    # Beanie query format using dict approach as seen in profile API
    logs = await TrackingLog.find(query).sort("-timestamp").limit(limit).to_list()
    
    # Format response mapping Beanie '_id' down to Pydantic 'id'
    results = []
    for log in logs:
        data = log.model_dump()
        data["id"] = str(log.id)
        results.append(TrackingLogResponse(**data))
        
    return results
