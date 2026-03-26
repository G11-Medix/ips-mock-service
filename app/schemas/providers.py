from datetime import datetime

from pydantic import BaseModel


class SpecialtyRead(BaseModel):
    id: int
    name: str


class ProviderRead(BaseModel):
    id: int
    full_name: str
    specialty_id: int


class SlotRead(BaseModel):
    provider_id: int
    slot_start: datetime
    available: bool
    blocked: bool
