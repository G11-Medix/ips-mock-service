from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.db.session import get_session
from app.models.entities import Appointment
from app.schemas.appointments import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentRead,
    AppointmentReschedule,
)
from app.services.appointments import (
    ensure_patient_exists,
    ensure_provider_exists,
    list_appointments,
    validate_slot,
)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, session: Session = Depends(get_session)) -> Appointment:
    ensure_patient_exists(session, payload.patient_id)
    provider = ensure_provider_exists(session, payload.provider_id)
    validate_slot(session, provider.id, payload.slot_start)

    appointment = Appointment(
        patient_id=payload.patient_id,
        provider_id=provider.id,
        specialty_id=provider.specialty_id,
        slot_start=payload.slot_start,
        status="scheduled",
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, session: Session = Depends(get_session)) -> Appointment:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.get("", response_model=list[AppointmentRead])
def get_appointments(
    patient_id: int | None = Query(default=None),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    session: Session = Depends(get_session),
) -> list[Appointment]:
    return list_appointments(session, patient_id=patient_id, from_date=from_date, to_date=to_date)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancel,
    session: Session = Depends(get_session),
) -> Appointment:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.status == "cancelled":
        raise HTTPException(status_code=409, detail="Appointment already cancelled")

    appointment.status = "cancelled"
    appointment.cancel_reason = payload.reason
    appointment.updated_at = datetime.utcnow()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    session: Session = Depends(get_session),
) -> Appointment:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.status != "scheduled":
        raise HTTPException(status_code=409, detail="Only scheduled appointments can be rescheduled")

    ensure_provider_exists(session, appointment.provider_id)
    validate_slot(session, appointment.provider_id, payload.new_slot_start, appointment_id=appointment.id)

    appointment.slot_start = payload.new_slot_start
    appointment.updated_at = datetime.utcnow()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment
