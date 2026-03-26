from datetime import datetime

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    patient_id: int
    provider_id: int
    slot_start: datetime


class AppointmentRead(BaseModel):
    id: int
    patient_id: int
    provider_id: int
    specialty_id: int
    slot_start: datetime
    status: str
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime


class AppointmentCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class AppointmentReschedule(BaseModel):
    new_slot_start: datetime
