

"""
screening.py — Beanie ODM Document for practitioner screening sessions.

This module defines the ``ScreeningSession`` document, which represents a single
clinical screening encounter conducted by a practitioner (doctor, nurse,
clinical officer, or CHV) for a given patient within the HealthBridge platform.

Each session can capture blood-pressure readings, a glucose reading, an
AI-generated clinical summary, referral recommendations, and patient consent
metadata as required by the Kenya Data Protection Act 2019.

Sub-models
----------
Classification
    Shared classification label + UI colour for BP and glucose readings.
BPReading
    A single blood-pressure measurement with systolic, diastolic, and
    classification metadata.
GlucoseReading
    A single glucose measurement with value, unit, test type, and
    classification metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from beanie import Document
from pydantic import BaseModel, Field, model_validator
from pymongo import DESCENDING, IndexModel

# Shared sub-models

class PractitionerRole(str, Enum):
    """Practitioner roles within the HealthBridge platform.
    str mixin stores readable strings in MongoDB, not integers.
    """
    DOCTOR = "doctor"
    NURSE = "nurse"
    CLINICAL_OFFICER = "clinical_officer"
    CHV = "chv"
class SessionStatus(str, Enum):
    """Lifecycle status of a screening session.
    
    Allows the frontend to distinguish between a session where the
    AI agent hasn't run yet vs one that completed or failed.
    """
    PENDING = "pending"         # vitals captured, agent not yet run
    PROCESSING = "processing"   # agent currently running
    COMPLETE = "complete"       # agent finished, summary available
    FAILED = "failed"           # agent ran but errored
GlucoseUnit = Literal["mmol_l", "mg_dl"]
"""Supported units for glucose measurements."""

GlucoseTestType = Literal["random", "fasting"]
"""Type of glucose test administered."""


class Classification(BaseModel):
    """Shared risk/severity classification for a clinical measurement.

    Used by both ``BPReading`` and ``GlucoseReading`` to carry a human-readable
    label and a hex colour string for consistent UI rendering.

    Attributes:
        label: Human-readable classification label (e.g. ``"Elevated"``,
            ``"Pre-diabetic"``).


    Example:
        >>> c = Classification(label="Normal")
        >>> c.label
        'Normal'
    """

    label: str = Field(..., description="Human-readable classification label.")


class BPReading(BaseModel):
    """A single blood-pressure measurement taken during a screening session.

    Readings are stored in insertion order so that averaging and trend
    detection can be performed without additional sorting.

    Attributes:
        systolic: Systolic blood pressure in mmHg.
        diastolic: Diastolic blood pressure in mmHg.
        classification: JNC-8 / ESC 2018 classification for this reading.
        timestamp: Timezone-aware UTC datetime at which the reading was taken.

    Example:
        >>> r = BPReading(
        ...     systolic=128,
        ...     diastolic=82,
        ...     classification=Classification(label="Elevated"),
        ...     timestamp=datetime.now(timezone.utc),
        ... )
        >>> r.systolic
        128
    """

    systolic: int = Field(..., ge=40, le=300, description="Systolic pressure in mmHg.")
    diastolic: int = Field(
        ..., ge=20, le=200, description="Diastolic pressure in mmHg."
    )
    classification: Classification = Field(
        ..., description="JNC-8 / ESC 2018 classification for this reading."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timezone-aware UTC datetime of the reading.",
    )


class GlucoseReading(BaseModel):
    """A single glucose measurement taken during a screening session.

    Attributes:
        value: Numeric glucose value in the units specified by ``unit``.
        unit: Measurement unit — ``"mmol_l"`` or ``"mg_dl"``.
        test_type: Whether the test was ``"random"`` or ``"fasting"``.
        classification: WHO / IDF classification for this reading.

    Example:
        >>> g = GlucoseReading(
        ...     value=5.6,
        ...     unit="mmol_l",
        ...     test_type="fasting",
        ...     classification=Classification(label="Normal", color="#4CAF50"),
        ... )
        >>> g.unit
        'mmol_l'
    """

    value: float = Field(
        ..., ge=0.0, description="Numeric glucose value in the specified unit."
    )
    unit: GlucoseUnit = Field(
        ..., description="Measurement unit: 'mmol_l' or 'mg_dl'."
    )
    test_type: GlucoseTestType = Field(
        ..., description="Test type: 'random' (non-fasting) or 'fasting'."
    )
    classification: Classification = Field(
        ..., description="WHO / IDF classification for this reading."
    )



# Main document


class ScreeningSession(Document):
    """A single practitioner-led screening session for a patient.

    A screening session is created each time a practitioner (identified by
    their Firebase UID) conducts a health screening for a patient (identified
    by their MongoDB ObjectId as a string).  The session stores all vitals
    collected, AI outputs, referral recommendations, and the consent record
    required under the Kenya Data Protection Act 2019.

    Attributes:
        patient_id: MongoDB ObjectId (as a plain string) referencing the
            corresponding Patient document.
        practitioner_id: Firebase UID of the practitioner who conducted the
            screening.
        practitioner_role: Role of the practitioner at the time of the
            screening.  One of: ``"doctor"``, ``"nurse"``,
            ``"clinical_officer"``, ``"chv"``.
        bp_readings: Ordered list of blood-pressure readings captured during
            the session.  Multiple readings are encouraged to support
            averaging and trend detection.
        glucose_reading: Optional glucose measurement; ``None`` when not
            captured.
        agent_summary: AI-generated one-page clinical summary produced by the
            HealthBridge Summary Agent.  ``None`` until the agent has run.
        referrals: Referral recommendation strings generated by the Safety
            Agent.  Empty list when no referrals are required.
        consent_given: ``True`` when the patient provided verbal consent
            before the session began.  Mandatory under Kenya Data Protection
            Act 2019 (KDPA 2019 § 30 — Sensitive Personal Data).
        consent_timestamp: Timezone-aware UTC datetime at which consent was
            recorded.  Must be provided when ``consent_given`` is ``True``.
        timestamp: Timezone-aware UTC datetime at which the screening was
            conducted.  Defaults to ``datetime.now(timezone.utc)`` at
            creation time.

    Collection:
        ``screening_sessions``

    Indexes:
        - ``(patient_id, timestamp DESC)`` — per-patient history queries.
        - ``(practitioner_id, timestamp DESC)`` — per-practitioner session lists.

    Raises:
        ValueError: If ``consent_given`` is ``True`` but ``consent_timestamp``
            is ``None``.

    Example:
        >>> session = ScreeningSession(
        ...     patient_id="64a1f2b3c4d5e6f7a8b9c0d1",
        ...     practitioner_id="firebase-uid-abc123",
        ...     practitioner_role="nurse",
        ...     consent_given=True,
        ...     consent_timestamp=datetime.now(timezone.utc),
        ... )
    """

    patient_id: str = Field(
        ...,
        description=(
            "MongoDB ObjectId (as a string) referencing the Patient document "
            "in the 'patients' collection."
        ),
    )
    practitioner_id: str = Field(
        ...,
        description="Firebase UID of the practitioner who conducted the screening.",
    )
    practitioner_role: PractitionerRole = Field(
        ...,
        description=(
            "Role of the practitioner. "
            "One of: 'doctor', 'nurse', 'clinical_officer', 'chv'."
        ),
    )
    bp_readings: list[BPReading] = Field(
        default_factory=list,
        description=(
            "Ordered list of blood-pressure readings taken during the session. "
            "Multiple readings are encouraged for averaging and trend detection."
        ),
    )
    glucose_reading: Optional[GlucoseReading] = Field(
        default=None,
        description=(
            "Optional glucose measurement. None when not captured during the session."
        ),
    )
    status: SessionStatus = Field(
        default=SessionStatus.PENDING,
        description=(
            "Lifecycle status of the session. PENDING until the AI agent runs, "
            "PROCESSING while running, COMPLETE when summary is available, "
            "FAILED if the agent errored."
        ),
    )
    agent_summary: Optional[str] = Field(
        default=None,
        description=(
            "AI-generated one-page clinical summary from the HealthBridge Summary "
            "Agent.  Plain text only.  None until the agent has processed "
            "the session."
        ),
    )
    habit_plan_raw: Optional[str] = Field(
        default=None,
        description="Raw habit plan output from the Habit Coach agent in plain text.",
    )
    referrals: list[str] = Field(
        default_factory=list,
        description=(
            "Referral recommendation strings generated by the Safety Agent. "
            "Empty list when no referrals are required."
        ),
    )
    consent_given: bool = Field(
        ...,
        description=(
            "True when the patient provided verbal consent before the session. "
            "Required under Kenya Data Protection Act 2019 (KDPA 2019 § 30)."
        ),
    )
    consent_timestamp: Optional[datetime] = Field(
        default=None,
        description=(
            "Timezone-aware UTC datetime at which the patient's verbal consent "
            "was recorded.  Must be set when consent_given is True."
        ),
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description=(
            "Timezone-aware UTC datetime at which the screening was conducted. "
            "Defaults to datetime.now(timezone.utc) at document creation."
        ),
    )


    # Validators
    

    @model_validator(mode="after")
    def _consent_timestamp_required(self) -> "ScreeningSession":
        """Enforce that consent_timestamp is provided when consent_given is True.

        Returns:
            The validated ``ScreeningSession`` instance unchanged.

        Raises:
            ValueError: When ``consent_given`` is ``True`` and
                ``consent_timestamp`` is ``None``.
        """
        if self.consent_given and self.consent_timestamp is None:
            raise ValueError(
                "consent_timestamp must be provided when consent_given is True. "
                "This is required for KDPA 2019 compliance."
            )
        return self

 
    # Beanie settings
    

    class Settings:
        """Beanie document settings for ``ScreeningSession``.

        Attributes:
            name: MongoDB collection name.
            indexes: Compound indexes for efficient time-ordered queries
                scoped by patient and by practitioner.
        """

        name = "screening_sessions"
        indexes = [
            IndexModel(
                [("patient_id", DESCENDING), ("timestamp", DESCENDING)],
                name="patient_timestamp_desc",
            ),
            IndexModel(
                [("practitioner_id", DESCENDING), ("timestamp", DESCENDING)],
                name="practitioner_timestamp_desc",
            ),
        ]
