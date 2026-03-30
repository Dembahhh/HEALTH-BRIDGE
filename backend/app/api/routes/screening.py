"""
screening.py — API router for practitioner screening submissions.

This module handles the practitioner screening submission endpoint,
which processes patient vitals, runs classifiers, and saves the session.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

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


class ScreeningSubmitRequest(BaseModel):
    """Request payload for submitting a new screening session.
    
    Must contain either an existing patient ID or data to create a new patient.
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


@router.post("/submit", response_model=ScreeningSession)
async def submit_screening(
    request: ScreeningSubmitRequest,
    current_user: dict = Depends(get_current_user),
) -> ScreeningSession:
    """Submit a practitioner screening session.

    Validates consent, handles new or existing patient, runs classifiers on
    provided vitals, calls the placeholder agent to generate a summary, and
    saves the session record.
    
    Args:
        request: The valid payload containing vitals and patient info.
        current_user: The authenticated practitioner.
        
    Returns:
        The saved ScreeningSession document.
        
    Raises:
        HTTPException: If consent is not given, player info is missing, or
            if glucose measurements are incomplete.
    """
    # 1. Validate consent_given
    if not request.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient consent is required",
        )

    # Validate patient_id or new_patient presence
    if not request.patient_id and not request.new_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either patient_id or new_patient data",
        )

    # Retrieve practitioner ID correctly, based on deps.py implementation
    practitioner_uid = getattr(current_user, "firebase_uid", current_user.get("uid"))

    # 2. Get or Create Patient
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
        resolved_patient_id = str(patient.id)
    else:
        # Cast to string safely, as validation ensures it's populated
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            patient = await Patient.get(ObjectId(request.patient_id))
        except InvalidId:
            patient = None
            
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {request.patient_id} not found",
            )
        resolved_patient_id = str(patient.id)

    # 3. Process BP classification
    try:
        bp_class_dict = classify_bp(request.bp_systolic, request.bp_diastolic)
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

    # 4. Process Glucose classification (if provided)
    glucose_reading: Optional[GlucoseReading] = None
    glucose_class_dict: Optional[Dict[str, Any]] = None

    if request.glucose_value is not None:
        if not request.glucose_unit or not request.glucose_test_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="glucose_unit and glucose_test_type are required when glucose_value is provided",
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
                label=glucose_class_dict["label"], color=glucose_class_dict["color"]
            ),
        )

    # 5. Build screening context dict
    screening_context: Dict[str, Any] = {
        "patient_name": patient.name,
        "patient_age": patient.age,
        "patient_sex": patient.sex,
        "bp_classification": bp_class_dict,
        "glucose_classification": glucose_class_dict,
        "practitioner_role": request.practitioner_role,
        "notes": request.notes,
    }

    # 6. Call screening summary generator service
    agent_output = await generate_screening_summary(screening_context)

    # 7. Save ScreeningSession document
    session = ScreeningSession(
        patient_id=resolved_patient_id,
        practitioner_id=practitioner_uid,
        practitioner_role=request.practitioner_role,
        bp_readings=[bp_reading],
        glucose_reading=glucose_reading,
        agent_summary=agent_output.get("summary", ""),
        habit_plan=agent_output.get("habit_plan", ""),
        referrals=agent_output.get("referrals", []),
        consent_given=True,
        consent_timestamp=datetime.now(timezone.utc),
    )
    
    await session.create()

    # 8. Return saved session
    return session
