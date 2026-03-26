from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.entities import Appointment, Provider, Specialty
from app.schemas.providers import ProviderRead, SlotRead, SpecialtyRead
from app.services.slots import blocked_slots, build_daily_slots

router = APIRouter(prefix="/api/v1", tags=["providers"])


@router.get("/specialties", response_model=list[SpecialtyRead])
def list_specialties(session: Session = Depends(get_session)) -> list[Specialty]:
    return session.exec(select(Specialty).order_by(Specialty.name)).all()


@router.get("/providers", response_model=list[ProviderRead])
def list_providers(
    specialty_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[Provider]:
    query = select(Provider)
    if specialty_id is not None:
        query = query.where(Provider.specialty_id == specialty_id)
    return session.exec(query.order_by(Provider.id)).all()


@router.get("/providers/{provider_id}/slots", response_model=list[SlotRead])
def provider_slots(provider_id: int, date: date, session: Session = Depends(get_session)) -> list[SlotRead]:
    provider = session.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    slots = build_daily_slots(provider_id, date)
    blocked = blocked_slots(provider_id, date)
    booked_rows = session.exec(
        select(Appointment).where(
            Appointment.provider_id == provider_id,
            Appointment.slot_start.in_(slots),
            Appointment.status == "scheduled",
        )
    ).all()
    booked = {row.slot_start for row in booked_rows}

    return [
        SlotRead(
            provider_id=provider_id,
            slot_start=slot,
            blocked=slot in blocked,
            available=(slot not in blocked and slot not in booked),
        )
        for slot in slots
    ]
