from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.config import get_settings
from app.models.entities import Appointment


def _slot_times() -> list[time]:
    result: list[time] = []
    current = datetime.combine(date.today(), time(8, 0))
    end_morning = datetime.combine(date.today(), time(12, 0))
    while current < end_morning:
        result.append(current.time())
        current += timedelta(minutes=30)

    current = datetime.combine(date.today(), time(14, 0))
    end_afternoon = datetime.combine(date.today(), time(17, 0))
    while current < end_afternoon:
        result.append(current.time())
        current += timedelta(minutes=30)

    return result


def build_daily_slots(provider_id: int, target_date: date) -> list[datetime]:
    settings = get_settings()
    tz = ZoneInfo(settings.timezone)
    if target_date.weekday() >= 5:
        return []

    slots: list[datetime] = []
    for slot_time in _slot_times():
        local_dt = datetime.combine(target_date, slot_time, tzinfo=tz)
        slots.append(local_dt.replace(tzinfo=None))
    return slots


def blocked_slots(provider_id: int, target_date: date) -> set[datetime]:
    settings = get_settings()
    slots = build_daily_slots(provider_id, target_date)
    if not slots:
        return set()

    seed_value = f"{settings.eps_slug}:{provider_id}:{target_date.isoformat()}".encode("utf-8")
    seed_hash = hashlib.sha256(seed_value).hexdigest()
    rnd = random.Random(seed_hash)

    block_ratio = rnd.uniform(0.10, 0.30)
    block_count = int(len(slots) * block_ratio)
    if block_count == 0:
        return set()

    indices = set(rnd.sample(range(len(slots)), block_count))
    return {slots[i] for i in indices}


def is_slot_available(session: Session, provider_id: int, slot_start: datetime, excluded_appointment_id: int | None = None) -> bool:
    appointment_query = select(Appointment).where(
        Appointment.provider_id == provider_id,
        Appointment.slot_start == slot_start,
        Appointment.status == "scheduled",
    )
    appointment = session.exec(appointment_query).first()
    if appointment is None:
        return True
    if excluded_appointment_id is not None and appointment.id == excluded_appointment_id:
        return True
    return False
