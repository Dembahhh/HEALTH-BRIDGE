"""
Trends API Routes

Endpoints for calculating health data trends and averages.
Used primarily to populate the user dashboard.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models.tracking import TrackingLog

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class BPTrendSummary(BaseModel):
    count: int = 0
    avg_systolic: Optional[int] = None
    avg_diastolic: Optional[int] = None
    min_systolic: Optional[int] = None
    max_systolic: Optional[int] = None
    latest_classification: Optional[str] = None
    trend: str = "stable"  # "improving" | "stable" | "worsening"
    readings: List[Dict[str, Any]] = []


class GlucoseTrendSummary(BaseModel):
    count: int = 0
    avg_value: Optional[float] = None
    latest_classification: Optional[str] = None
    trend: str = "stable"
    readings: List[Dict[str, Any]] = []


class MedicationTrendSummary(BaseModel):
    adherence_percent: float = 0.0
    total_logged: int = 0
    taken_count: int = 0
    skipped_count: int = 0


class TrendsSummaryResponse(BaseModel):
    bp: BPTrendSummary
    glucose: GlucoseTrendSummary
    medication: MedicationTrendSummary
    period_days: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(current_user) -> str:
    """Extract Firebase UID safely from the user object/dict."""
    if isinstance(current_user, dict):
        return current_user.get("uid", "")
    return getattr(current_user, "firebase_uid", str(current_user.id))


def _calculate_bp_trend(last_7_days_avg: Optional[float], prev_7_days_avg: Optional[float]) -> str:
    """Compare recent 7-day average systolic to previous 7-day average."""
    if last_7_days_avg is None or prev_7_days_avg is None:
        return "stable"
    diff = last_7_days_avg - prev_7_days_avg
    if diff <= -5.0:
        return "improving"
    if diff >= 5.0:
        return "worsening"
    return "stable"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=TrendsSummaryResponse)
async def get_trends_summary(
    current_user: CurrentUser,
    days: int = Query(30, ge=7, le=90),
):
    """
    Get aggregated health trends for the dashboard.
    
    Returns averages, adherence percentages, and trend direction (improving/worsening).
    """
    uid = _uid(current_user)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Base match for the requested period
    base_match = {
        "user_id": uid,
        "timestamp": {"$gte": start_date, "$lte": end_date}
    }
    
    # Fetch all logs in period for manual aggregation
    # Since we are filtering by user and relatively small date windows (<90 days),
    # fetching the documents and doing array processing in Python is fast and avoids
    # highly complex MongoDB aggregation pipelines for the trend calculation logic.
    logs = await TrackingLog.find(base_match).sort("-timestamp").to_list()
    
    # ── Initialize summary blocks ──
    bp = BPTrendSummary()
    glucose = GlucoseTrendSummary()
    meds = MedicationTrendSummary()
    
    # Time boundaries for trend calculation (last 7 days vs previous 7 days)
    now = datetime.utcnow()
    t_minus_7 = now - timedelta(days=7)
    t_minus_14 = now - timedelta(days=14)
    
    # BP accumulators
    bp_sys_last_7 = []
    bp_sys_prev_7 = []
    all_sys = []
    all_dia = []
    
    for log in logs:
        # BP Processing
        if log.log_type == "bp" and log.systolic and log.diastolic:
            bp.count += 1
            all_sys.append(log.systolic)
            all_dia.append(log.diastolic)
            
            # Chart reading
            if len(bp.readings) < 20:
                bp.readings.insert(0, {
                    "timestamp": log.timestamp.isoformat(),
                    "systolic": log.systolic,
                    "diastolic": log.diastolic
                })
            
            # Latest classification
            if not bp.latest_classification and log.bp_classification:
                bp.latest_classification = log.bp_classification.get("category")
                
            # Trend buckets
            if log.timestamp >= t_minus_7:
                bp_sys_last_7.append(log.systolic)
            elif t_minus_14 <= log.timestamp < t_minus_7:
                bp_sys_prev_7.append(log.systolic)
                
        # Glucose Processing
        elif log.log_type == "glucose" and log.glucose_value is not None:
            glucose.count += 1
            
            # Chart reading
            if len(glucose.readings) < 20:
                glucose.readings.insert(0, {
                    "timestamp": log.timestamp.isoformat(),
                    "value": log.glucose_value,
                    "test_type": log.glucose_test_type
                })
                
            # Latest classification
            if not glucose.latest_classification and log.glucose_classification:
                glucose.latest_classification = log.glucose_classification.get("category")
                
        # Medication Processing
        elif log.log_type == "medication" and log.medications:
            for med in log.medications:
                meds.total_logged += 1
                if med.taken:
                    meds.taken_count += 1
                else:
                    meds.skipped_count += 1
                    
    # ── Finalize BP metrics ──
    if bp.count > 0:
        bp.avg_systolic = sum(all_sys) // bp.count
        bp.avg_diastolic = sum(all_dia) // bp.count
        bp.min_systolic = min(all_sys)
        bp.max_systolic = max(all_sys)
        
    last_7_avg = sum(bp_sys_last_7) / len(bp_sys_last_7) if bp_sys_last_7 else None
    prev_7_avg = sum(bp_sys_prev_7) / len(bp_sys_prev_7) if bp_sys_prev_7 else None
    bp.trend = _calculate_bp_trend(last_7_avg, prev_7_avg)
    
    # ── Finalize Glucose metrics ──
    if glucose.count > 0:
        all_gluc = [r["value"] for r in glucose.readings]  # rough approx using recent
        glucose.avg_value = round(sum(all_gluc) / len(all_gluc), 1)
        
    # ── Finalize Medication metrics ──
    if meds.total_logged > 0:
        meds.adherence_percent = round((meds.taken_count / meds.total_logged) * 100, 1)

    return TrendsSummaryResponse(
        bp=bp,
        glucose=glucose,
        medication=meds,
        period_days=days
    )
