from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.entities import Appointment, Paciente, Provider
from app.services.slots import blocked_slots, build_daily_slots, is_slot_available


def ensure_patient_exists(session: Session, patient_id: int) -> None:
    patient = session.get(Paciente, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")


def ensure_provider_exists(session: Session, provider_id: int) -> Provider:
    provider = session.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Prestador no encontrado")
    return provider


def validate_slot(session: Session, provider_id: int, slot_start: datetime, appointment_id: int | None = None) -> None:
    day_slots = build_daily_slots(provider_id, slot_start.date())
    if slot_start not in day_slots:
        raise HTTPException(status_code=400, detail="El cupo esta fuera del horario del prestador")

    blocked = blocked_slots(provider_id, slot_start.date())
    if slot_start in blocked:
        raise HTTPException(status_code=409, detail="El cupo se encuentra bloqueado")

    if not is_slot_available(session, provider_id, slot_start, excluded_appointment_id=appointment_id):
        raise HTTPException(status_code=409, detail="El cupo ya fue reservado")


def list_appointments(
    session: Session,
    patient_id: int | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> list[Appointment]:
    query = select(Appointment)
    if patient_id is not None:
        query = query.where(Appointment.patient_id == patient_id)
    if from_date is not None:
        query = query.where(Appointment.slot_start >= from_date)
    if to_date is not None:
        query = query.where(Appointment.slot_start <= to_date)

    return session.exec(query.order_by(Appointment.slot_start)).all()
