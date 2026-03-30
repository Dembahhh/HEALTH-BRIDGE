"""
patients.py — Patient management API routes for HealthBridge practitioners.

Endpoints
---------
GET  /api/patients/search          — Full-text patient search by name or phone.
POST /api/patients/                — Create a new patient record.
GET  /api/patients/{patient_id}/history — Combined screening + tracking history.

All routes require a valid Firebase auth token via ``Depends(get_current_user)``.
"""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.models.patient import Patient, PatientCreate
from app.models.screening import ScreeningSession
from app.models.tracking import TrackingLog

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid(current_user: Any) -> str:
    """Extract the Firebase UID from a user object or dict.

    Args:
        current_user: Either a Beanie ``User`` document or a plain dict
            returned by the auth dependency on token-only paths.

    Returns:
        The Firebase UID string.
    """
    if isinstance(current_user, dict):
        return current_user.get("uid", "")
    return getattr(current_user, "firebase_uid", str(current_user.id))


def _patient_to_dict(patient: Patient) -> dict[str, Any]:
    """Serialise a ``Patient`` document to a JSON-safe dict.

    Converts the Beanie ``PydanticObjectId`` to a plain string ``_id`` so the
    frontend can use it directly as a reference key.

    Args:
        patient: A ``Patient`` Beanie document.

    Returns:
        Dict representation with ``_id`` as a string.
        Note:
        Changed : mode="json" forces Pydantic v2 to convert ALL types to JSON-safe
     primitives, including PydanticObjectId -> str, datetime -> ISO string
    """
    data = patient.model_dump(mode="json")
    data["_id"] = str(patient.id)
    #remove internal 'id key Beanie adds to avoid duplication
    data.pop("id", None)
    return data


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/search", summary="Search patients by name or phone")
async def search_patients(
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, description="Search term (name or phone)"),
) -> list[dict[str, Any]]:
    """Search patients by name or phone using case-insensitive regex.

    Requires the query string to be at least 2 characters long to avoid
    returning the entire collection.  Returns up to 10 matching records.

    Args:
        current_user: Authenticated practitioner injected by the auth dependency.
        q: Partial name or phone number to search for.

    Returns:
        A list of up to 10 patient dicts, each with ``_id`` as a string.

    Raises:
        HTTPException 400: If the search query is shorter than 2 characters.

    Example:
        GET /api/patients/search?q=jane
    """
    if len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query too short — please enter at least 2 characters.",
        )

    pattern = {"$regex": q.strip(), "$options": "i"}
    query_filter = {"$or": [{"name": pattern}, {"phone": pattern}]}

    patients = (
        await Patient.find(query_filter)
        .limit(10)
        .to_list()
    )

    return [_patient_to_dict(p) for p in patients]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient record",
)
async def create_patient(
    body: PatientCreate,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Create a new patient record for the authenticated practitioner.

    The ``created_by`` field is injected server-side from the authenticated
    user's Firebase UID and is **not** accepted from the request body.

    Args:
        body: ``PatientCreate`` request payload.  Only ``name`` is required.
        current_user: Authenticated practitioner injected by the auth dependency.

    Returns:
        The newly created patient document as a dict with ``_id`` as a string.

    Example:
        POST /api/patients/
        Body: {"name": "Jane Doe", "phone": "+254712345678", "age": 34, "sex": "female"}
    """
    uid = _uid(current_user)
    now = datetime.now(timezone.utc)

    patient = Patient(
        name=body.name,
        phone=body.phone,
        age=body.age,
        sex=body.sex,
        notes=body.notes,
        created_by=uid,
        created_at=now,
        updated_at=now,
    )

    await patient.insert()
    logger.info("Patient created: id=%s by practitioner=%s", patient.id, uid)

    return _patient_to_dict(patient)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@router.get("/{patient_id}/history", summary="Get combined patient history")
async def get_patient_history(
    patient_id: str,
    current_user: CurrentUser,  # noqa: ARG001 — auth guard; UID unused here
) -> list[dict[str, Any]]:
    """Return a combined, time-ordered history for a specific patient.

    Merges ``ScreeningSession`` records and ``TrackingLog`` records for the
    given patient, sorted by timestamp descending (most recent first).  Each
    item includes a ``"type"`` field (``"screening"`` or ``"tracking"``) so the
    frontend can render them with different UI components.

    Args:
        patient_id: MongoDB ObjectId string of the target patient document.
        current_user: Authenticated practitioner injected by the auth dependency.

    Returns:
        A time-sorted list of history event dicts, each with a ``"type"`` key.

    Raises:
        HTTPException 400: If ``patient_id`` is not a valid MongoDB ObjectId.
        HTTPException 404: If no patient with the given ID exists.

    Example:
        GET /api/patients/64a1f2b3c4d5e6f7a8b9c0d1/history
    """
    # Validate ObjectId format up-front for a clear 400 error
    try:
        ObjectId(patient_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{patient_id}' is not a valid patient ID.",
        )

    # Confirm the patient exists
    patient = await Patient.get(patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    # Fetch screening sessions and tracking logs in parallel
    screening_docs, tracking_docs = await _fetch_history(patient_id, patient)

    # Merge and tag events with their source type
    events: list[dict[str, Any]] = []

    for session in screening_docs:
        data = session.model_dump(mode="json")
        data["_id"] = str(session.id)
        data.pop("id", None)
        data["type"] = "screening"
        # Normalise timestamp key so both types share a common sort field
        data.setdefault("timestamp", session.timestamp.isoformat() if session.timestamp else None)
        events.append(data)

    for log in tracking_docs:
        data = log.model_dump(mode="json")
        data["_id"] = str(log.id)
        data.pop("id", None)
        data["type"] = "tracking"
        data.setdefault("timestamp", log.timestamp.isoformat() if log.timestamp else None)
        events.append(data)

    # Sort descending — most recent first
    events.sort(
        key=lambda e: e.get("timestamp") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    return events


async def _fetch_history(
    patient_id: str,
    patient: Patient,
) -> tuple[list[ScreeningSession], list[TrackingLog]]:
    """Concurrently fetch screening sessions and tracking logs for a patient.

    Args:
        patient_id: MongoDB ObjectId string of the target patient.

    Returns:
        A tuple of ``(screening_sessions, tracking_logs)``.
    """
    
    screening_filter: dict = {"$or": [{"patient_id": patient_id}]}
    tracking_filter: dict = {"$or": [{"patient_id": patient_id}]}
    
    if patient.firebase_uid:
        screening_filter["$or"].append({"user_id": patient.firebase_uid})
        tracking_filter["$or"].append({"user_id": patient.firebase_uid})

    screening_task = asyncio.create_task(
        ScreeningSession.find(screening_filter)
        .sort("-timestamp")
        .to_list()
    )
    tracking_task = asyncio.create_task(
        TrackingLog.find(tracking_filter)
        .sort("-timestamp")
        .to_list()
    )

    screening_docs, tracking_docs = await asyncio.gather(
        screening_task, tracking_task
    )
    return screening_docs, tracking_docs
