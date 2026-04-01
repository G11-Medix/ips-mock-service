from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.db.session import get_session
from app.models.entities import Appointment
from app.schemas.appointments import (
    CitaCancelar,
    CitaCrear,
    CitaRead,
    CitaReprogramar,
)
from app.services.appointments import (
    ensure_patient_exists,
    ensure_provider_exists,
    list_appointments,
    validate_slot,
)

router = APIRouter(prefix="/api/v1/citas", tags=["citas"])


def _to_cita_read(appointment: Appointment) -> CitaRead:
    return CitaRead(
        id=appointment.id,
        id_paciente=appointment.patient_id,
        id_prestador=appointment.provider_id,
        id_especialidad=appointment.specialty_id,
        fecha_hora_cupo=appointment.slot_start,
        estado=appointment.status,
        motivo_cancelacion=appointment.cancel_reason,
        fecha_creacion=appointment.created_at,
        fecha_actualizacion=appointment.updated_at,
    )


@router.post("", response_model=CitaRead, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: CitaCrear, session: Session = Depends(get_session)) -> CitaRead:
    ensure_patient_exists(session, payload.id_paciente)
    provider = ensure_provider_exists(session, payload.id_prestador)
    validate_slot(session, provider.id, payload.fecha_hora_cupo)

    appointment = Appointment(
        patient_id=payload.id_paciente,
        provider_id=provider.id,
        specialty_id=provider.specialty_id,
        slot_start=payload.fecha_hora_cupo,
        status="scheduled",
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return _to_cita_read(appointment)


@router.get("/{id_cita}", response_model=CitaRead)
def get_appointment(id_cita: int, session: Session = Depends(get_session)) -> CitaRead:
    appointment = session.get(Appointment, id_cita)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return _to_cita_read(appointment)


@router.get("", response_model=list[CitaRead])
def get_appointments(
    id_paciente: int | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[CitaRead]:
    appointments = list_appointments(session, patient_id=id_paciente, from_date=desde, to_date=hasta)
    return [_to_cita_read(row) for row in appointments]


@router.patch("/{id_cita}/cancelar", response_model=CitaRead)
def cancel_appointment(
    id_cita: int,
    payload: CitaCancelar,
    session: Session = Depends(get_session),
) -> CitaRead:
    appointment = session.get(Appointment, id_cita)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    if appointment.status == "cancelled":
        raise HTTPException(status_code=409, detail="La cita ya fue cancelada")

    appointment.status = "cancelled"
    appointment.cancel_reason = payload.motivo
    appointment.updated_at = datetime.utcnow()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return _to_cita_read(appointment)


@router.patch("/{id_cita}/reprogramar", response_model=CitaRead)
def reschedule_appointment(
    id_cita: int,
    payload: CitaReprogramar,
    session: Session = Depends(get_session),
) -> CitaRead:
    appointment = session.get(Appointment, id_cita)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    if appointment.status != "scheduled":
        raise HTTPException(status_code=409, detail="Solo las citas programadas pueden reprogramarse")

    ensure_provider_exists(session, appointment.provider_id)
    validate_slot(
        session,
        appointment.provider_id,
        payload.nueva_fecha_hora_cupo,
        appointment_id=appointment.id,
    )

    appointment.slot_start = payload.nueva_fecha_hora_cupo
    appointment.updated_at = datetime.utcnow()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return _to_cita_read(appointment)
