"""Pydantic request schemas with explicit server-side validation."""

import re
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

ExperienceType = Literal["peth-stories-walk", "private-group"]
RegistrationStatus = Literal["INTEREST_RECEIVED", "CONTACTED", "WAITLISTED", "CLOSED"]
SessionStatus = Literal["DRAFT", "PUBLISHED", "CANCELLED", "COMPLETED"]


class RegistrationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    preferred_date: Optional[str] = Field(default=None, max_length=10)
    guest_count: int = Field(ge=1, le=12)
    experience_type: ExperienceType
    notes: Optional[str] = Field(default=None, max_length=1000)
    consent: bool
    session_id: Optional[int] = Field(default=None, ge=1)
    website: str = Field(default="", max_length=200)  # honeypot — must stay empty

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Please enter a valid email address, e.g. name@example.com.")
        return value

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Please enter your full name.")
        return value

    @field_validator("preferred_date")
    @classmethod
    def _valid_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Preferred date must be a valid date (YYYY-MM-DD).") from exc

    @field_validator("notes")
    @classmethod
    def _clean_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("consent")
    @classmethod
    def _consent_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Please confirm that this is an interest registration, not a booking.")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=512)


class StatusUpdate(BaseModel):
    status: RegistrationStatus


# --------------------------------------------------------------------------
# Walk sessions
# --------------------------------------------------------------------------


class SessionBase(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10, max_length=1000)
    walk_date: str = Field(min_length=10, max_length=10)
    start_time: str = Field(min_length=5, max_length=5)
    duration_minutes: int = Field(ge=15, le=480)
    meeting_point: str = Field(min_length=3, max_length=200)
    capacity: Optional[int] = Field(default=None, ge=1, le=60)
    inclusions: Optional[str] = Field(default=None, max_length=600)

    @field_validator("title", "meeting_point")
    @classmethod
    def _clean_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Please provide a meaningful value.")
        return value

    @field_validator("description")
    @classmethod
    def _clean_description(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 10:
            raise ValueError("Please describe the session in at least 10 characters.")
        return value

    @field_validator("walk_date")
    @classmethod
    def _valid_date(cls, value: str) -> str:
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Walk date must be a valid date (YYYY-MM-DD).") from exc

    @field_validator("start_time")
    @classmethod
    def _valid_time(cls, value: str) -> str:
        if not TIME_RE.match(value):
            raise ValueError("Start time must use 24-hour HH:MM format, e.g. 09:30.")
        return value

    @field_validator("inclusions")
    @classmethod
    def _clean_inclusions(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class SessionCreate(SessionBase):
    pass


class SessionUpdate(SessionBase):
    pass


class SessionStatusUpdate(BaseModel):
    status: SessionStatus