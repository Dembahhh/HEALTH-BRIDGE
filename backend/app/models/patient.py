# NOTE FOR DEVELOPERS:
# Remember to register `Patient` in `init_beanie()` inside `app/config/database.py`.
# Example:
#   await init_beanie(database=db, document_models=[..., Patient])
# Failure to do so will cause Beanie to silently ignore this collection at startup.

"""
patient.py — Beanie ODM Document for patient records in HealthBridge.

This module defines the ``Patient`` document, which represents a patient record
created by a health practitioner (doctor, nurse, clinical officer, or CHV)
within the HealthBridge platform.

Each record stores identifying and demographic information for a patient, along
with a reference to the practitioner who created it.  Phone number serves as
the primary search identifier in the field.

Models
------
Patient
    Beanie Document persisted to the ``patients`` MongoDB collection.
PatientCreate
    Pydantic ``BaseModel`` used as the request body when creating a new patient
    record via the API.  Only ``name`` is required; all other fields are optional.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel, TEXT

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

PatientSex = Literal["male", "female"]
"""Allowed biological-sex / gender values for a patient record."""


# ---------------------------------------------------------------------------
# Beanie Document
# ---------------------------------------------------------------------------


class Patient(Document):
    """A patient record created by a HealthBridge practitioner.

    Each ``Patient`` document represents a single individual whose health data
    is managed within the platform.  The record is created by a practitioner
    (identified by their Firebase UID) and may be updated over time as new
    information becomes available.

    Phone number is the primary search identifier used when looking up existing
    patients before creating a duplicate record.

    Attributes:
        name: Full name of the patient.
        phone: Optional phone number.  Used as the primary search key to avoid
            duplicate patient records.
        age: Optional age of the patient in years.
        sex: Optional biological sex / gender — one of ``"male"`` or ``"female"``.
        created_by: Firebase UID of the practitioner who created this record.
        created_at: Timezone-aware UTC datetime at which the document was
            first persisted.  Defaults to ``datetime.now(timezone.utc)``.
        updated_at: Timezone-aware UTC datetime of the most recent update.
            Must be refreshed explicitly on every write; defaults to
            ``datetime.now(timezone.utc)`` at creation.
        notes: Optional free-text clinical or administrative notes attached to
            the patient record.

    Collection:
        ``patients``

    Indexes:
        - Text index on ``(name, phone)`` — supports full-text search across
          patient names and phone numbers.
        - Ascending index on ``created_by`` — efficient per-practitioner queries.

    Example:
        >>> patient = Patient(
        ...     name="Jane Doe",
        ...     phone="+254712345678",
        ...     age=34,
        ...     sex="female",
        ...     created_by="firebase-uid-abc123",
        ... )
        >>> patient.name
        'Jane Doe'
    """

    name: str = Field(
        ...,
        description="Full name of the patient.",
    )
    phone: Optional[str] = Field(
        default=None,
        description=(
            "Patient phone number.  Used as the primary search identifier "
            "to prevent duplicate records."
        ),
    )
    firebase_uid: Optional[str] = Field(
        default=None,                        
        description="Firebase UID of the patient's own account, if they have one.",
    )
    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=150,
        description="Age of the patient in years.",
    )
    sex: Optional[PatientSex] = Field(
        default=None,
        description="Biological sex / gender: 'male' or 'female'.",
    )
    created_by: str = Field(
        ...,
        description="Firebase UID of the practitioner who created this record.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description=(
            "Timezone-aware UTC datetime at which this document was first persisted."
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description=(
            "Timezone-aware UTC datetime of the most recent update to this document. "
            "Must be refreshed explicitly on every write."
        ),
    )
    notes: Optional[str] = Field(
        default=None,
        description="Free-text clinical or administrative notes for this patient.",
    )

    # ------------------------------------------------------------------
    # Beanie settings
    # ------------------------------------------------------------------

    class Settings:
        """Beanie document settings for ``Patient``.

        Attributes:
            name: MongoDB collection name.
            indexes: Text index on ``(name, phone)`` for full-text search,
                plus an ascending index on ``created_by`` for practitioner
                scoped queries.
        """

        name = "patients"
        indexes = [
            IndexModel(
                [("name", TEXT), ("phone", TEXT)],
                name="patient_text_search",
            ),
            IndexModel(
                [("created_by", ASCENDING)],
                name="created_by_asc",
            ),
        ]


# ---------------------------------------------------------------------------
# API request model
# ---------------------------------------------------------------------------


class PatientCreate(BaseModel):
    """Request body schema for creating a new patient record.

    Only ``name`` is required.  The practitioner's Firebase UID (``created_by``)
    is injected server-side from the authenticated request context and is
    therefore **not** part of this model.

    Attributes:
        name: Full name of the patient.  Required.
        phone: Optional phone number used as the primary search identifier.
        age: Optional age of the patient in years.
        sex: Optional biological sex / gender — one of ``"male"``,
            ``"female"``, or ``"other"``.
        notes: Optional free-text clinical or administrative notes.

    Example:
        >>> payload = PatientCreate(
        ...     name="John Kamau",
        ...     phone="+254798765432",
        ...     age=45,
        ...     sex="male",
        ... )
        >>> payload.name
        'John Kamau'
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Full name of the patient.",
    )
    phone: Optional[str] = Field(
        default=None,
        description="Patient phone number.",
    )
    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=150,
        description="Age of the patient in years.",
    )
    sex: Optional[PatientSex] = Field(
        default=None,
        description="Biological sex / gender: 'male' or 'female'.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Free-text clinical or administrative notes.",
    )
