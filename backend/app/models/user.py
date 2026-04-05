"""
User Model

MongoDB document model for user accounts.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional
from beanie import Document, Indexed, before_event, Replace, SaveChanges
from pydantic import EmailStr, Field


class UserRole(str, Enum):
    """
    Explicit role enum — str mixin means it serialises to
    "patient" / "practitioner" / "admin" in MongoDB and JSON,
    not 0 / 1 / 2. Readable in the DB, safe to add new roles later.
    """
    PATIENT = "patient"
    PRACTITIONER = "practitioner"
    ADMIN = "admin"


class User(Document):
    """User document model."""

#identity
    email: Annotated[EmailStr, Indexed(unique=True)]
    firebase_uid: Annotated[str, Indexed(unique=True)]
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: UserRole = UserRole.PATIENT 
    is_active: bool = True
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None        
    phone_number: Optional[str] = None
    consent_given: bool = False
    consent_given_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

    @before_event(Replace, SaveChanges)
    def update_timestamp(self):
        """
        Automatically update updated_at before every save.
        Beanie calls this — callers never need to remember.
        """
        self.updated_at = datetime.utcnow()