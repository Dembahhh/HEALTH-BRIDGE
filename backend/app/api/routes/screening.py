"""screening.py — API router for practitioner screening submissions.

This module handles the practitioner screening submission endpoint,
which processes patient vitals, runs classifiers, and saves the session.
It also provides a seal endpoint for overwriting AI-generated fields
with Lit Protocol encrypted blobs from the frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.classifiers.bp import classify_bp
from app.core.classifiers.glucose import classify_glucose
from app.models.patient import Patient, PatientCreate
from app.models.screening import (
    BPReading,
    Classification,
    GlucoseReading,
    GlucoseTestType,
    GlucoseUnit,
    PractitionerRole,
    ScreeningSession,
)
from app.services.screening import generate_screening_summary

router = APIRouter()

#Request / payload models 

class ScreeningSubmitRequest(BaseModel):
    """Request payload for submitting a new screening session.

    Must contain either an existing patient ID or inline data to create
    a new patient record.
    """

    patient_id: Optional[str] = Field(
        default=None, description="ID of an existing patient document."
    )
    new_patient: Optional[PatientCreate] = Field(
        default=None, description="Data to create a new patient inline."
    )
    bp_systolic: int = Field(
        ..., description="Systolic blood pressure in mmHg.", ge=40, le=300
    )
    bp_diastolic: int = Field(
        ..., description="Diastolic blood pressure in mmHg.", ge=20, le=200
    )
    glucose_value: Optional[float] = Field(
        default=None, description="Optional glucose reading value.", ge=0.0
    )
    glucose_unit: Optional[GlucoseUnit] = Field(
        default=None, description="Measurement unit ('mmol_l' or 'mg_dl')."
    )
    glucose_test_type: Optional[GlucoseTestType] = Field(
        default=None, description="Test type ('random' or 'fasting')."
    )
    practitioner_role: PractitionerRole = Field(
        ..., description="Role of the practitioner conducting the screening."
    )
    consent_given: bool = Field(
        ..., description="Whether the patient provided verbal consent."
    )
    notes: Optional[str] = Field(
        default=None, description="Optional clinical notes from the practitioner."
    )


class SealPayload(BaseModel):
    """Payload for overwriting sensitive fields with Lit-encrypted blobs.

    Both fields are optional so the frontend can seal them independently.
    Encrypted values are prefixed with ``__lit_enc__:``.
    """

    agent_summary: Optional[str] = Field(
        default=None,
        description="Encrypted agent summary blob (prefixed __lit_enc__:).",
    )
    habit_plan_raw: Optional[str] = Field(
        default=None,
        description="Encrypted habit plan blob (prefixed __lit_enc__:).",
    )

# Helpers 

def _resolve_practitioner_uid(current_user: Any) -> str:
    """Extract the practitioner's Firebase UID from the auth dependency.

    Args:
        current_user: Object or dict returned by ``get_current_user``.

    Returns:
        The practitioner's UID string.
    """
    return getattr(current_user, "firebase_uid", None) or current_user.get("uid")


async def _get_patient_or_404(patient_id: str) -> Patient:
    """Load a patient by ObjectId string or raise 404.

    Args:
        patient_id: MongoDB ObjectId as a string.

    Returns:
        The resolved Patient document.

    Raises:
        HTTPException: 404 if the patient does not exist or the ID is invalid.
    """
    try:
        patient = await Patient.get(ObjectId(patient_id))
    except InvalidId:
        patient = None

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found",
        )
    return patient

# Routes

@router.post("/submit", response_model=ScreeningSession)
async def submit_screening(
    request: ScreeningSubmitRequest,
    current_user: Any = Depends(get_current_user),
) -> ScreeningSession:
    """Submit a practitioner screening session.

    Validates consent, resolves or creates the patient, runs BP and optional
    glucose classifiers, generates an AI summary, and persists the session.

    Args:
        request: Validated payload containing vitals and patient info.
        current_user: The authenticated practitioner (injected by FastAPI).

    Returns:
        The saved ``ScreeningSession`` document.

    Raises:
        HTTPException 400: Consent not given, patient info missing, or
            incomplete glucose measurements.
        HTTPException 404: Referenced patient_id does not exist.
    """
    # 1. Validate consent
    if not request.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient consent is required",
        )

    if not request.patient_id and not request.new_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either patient_id or new_patient data",
        )

    practitioner_uid: str = _resolve_practitioner_uid(current_user)

    # 2. Get or create patient
    if request.new_patient:
        patient = Patient(
            name=request.new_patient.name,
            phone=request.new_patient.phone,
            age=request.new_patient.age,
            sex=request.new_patient.sex,
            notes=request.new_patient.notes,
            created_by=practitioner_uid,
        )
        await patient.create()
    else:
        patient = await _get_patient_or_404(request.patient_id)

    resolved_patient_id: str = str(patient.id)

    # 3. BP classification
    try:
        bp_class_dict: dict[str, Any] = classify_bp(
            request.bp_systolic, request.bp_diastolic
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid blood pressure reading: {e}",
        )

    bp_reading = BPReading(
        systolic=request.bp_systolic,
        diastolic=request.bp_diastolic,
        classification=Classification(
            label=bp_class_dict["label"], color=bp_class_dict["color"]
        ),
        timestamp=datetime.now(timezone.utc),
    )

    # 4. Glucose classification (optional)
    glucose_reading: Optional[GlucoseReading] = None
    glucose_class_dict: Optional[dict[str, Any]] = None

    if request.glucose_value is not None:
        if not request.glucose_unit or not request.glucose_test_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "glucose_unit and glucose_test_type are required "
                    "when glucose_value is provided"
                ),
            )
        try:
            glucose_class_dict = classify_glucose(
                value=request.glucose_value,
                test_type=request.glucose_test_type,
                unit=request.glucose_unit,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid glucose reading: {e}",
            )

        glucose_reading = GlucoseReading(
            value=request.glucose_value,
            unit=request.glucose_unit,
            test_type=request.glucose_test_type,
            classification=Classification(
                label=glucose_class_dict["label"],
                color=glucose_class_dict["color"],
            ),
        )

    # 5. Build screening context
    screening_context: dict[str, Any] = {
        "patient_name": patient.name,
        "patient_age": patient.age,
        "patient_sex": patient.sex,
        "bp_classification": bp_class_dict,
        "glucose_classification": glucose_class_dict,
        "practitioner_role": request.practitioner_role,
        "notes": request.notes,
    }

    # 6. Generate agent summary
    agent_output: dict[str, Any] = await generate_screening_summary(
        screening_context
    )

    # 7. Save session
    session = ScreeningSession(
        patient_id=resolved_patient_id,
        practitioner_id=practitioner_uid,
        practitioner_role=request.practitioner_role,
        bp_readings=[bp_reading],
        glucose_reading=glucose_reading,
        agent_summary=agent_output.get("summary", ""),
        habit_plan_raw=agent_output.get("habit_plan", ""),
        referrals=agent_output.get("referrals", []),
        consent_given=True,
        consent_timestamp=datetime.now(timezone.utc),
    )

    await session.create()
    return session

#Seal endpoint (Lit Protocol encryption) 

@router.patch("/{session_id}/seal", response_model=ScreeningSession)
async def seal_screening_session(
    session_id: str,
    payload: SealPayload,
    current_user: Any = Depends(get_current_user),
) -> ScreeningSession:
    """Overwrite agent_summary and habit_plan_raw with Lit-encrypted blobs.

    Called from the frontend after the ScreeningWizard receives the AI
    output.  Only the practitioner who created the session may seal it.

    Args:
        session_id: MongoDB ObjectId string of the ScreeningSession.
        payload: Encrypted blobs for agent_summary and/or habit_plan_raw.
        current_user: The authenticated practitioner (injected by FastAPI).

    Returns:
        The updated ``ScreeningSession`` document.

    Raises:
        HTTPException 404: Session not found or invalid ObjectId.
        HTTPException 403: Caller is not the session's practitioner.
    """
    try:
        session = await ScreeningSession.get(ObjectId(session_id))
    except InvalidId:
        session = None

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening session {session_id} not found",
        )

    practitioner_uid: str = _resolve_practitioner_uid(current_user)
    if session.practitioner_id != practitioner_uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to seal this session",
        )

    if payload.agent_summary is not None:
        session.agent_summary = payload.agent_summary
    if payload.habit_plan_raw is not None:
        session.habit_plan_raw = payload.habit_plan_raw

    await session.save()
    return session