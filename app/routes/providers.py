from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.entities import Appointment, Provider, Specialty
from app.schemas.providers import CupoRead, EspecialidadRead, PrestadorRead
from app.services.slots import blocked_slots, build_daily_slots

router = APIRouter(prefix="/api/v1", tags=["prestadores"])


@router.get("/especialidades", response_model=list[EspecialidadRead])
def list_specialties(session: Session = Depends(get_session)) -> list[EspecialidadRead]:
    specialties = session.exec(select(Specialty).order_by(Specialty.name)).all()
    return [EspecialidadRead(id=row.id, nombre=row.name) for row in specialties]


@router.get("/prestadores", response_model=list[PrestadorRead])
def list_providers(
    id_especialidad: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[PrestadorRead]:
    query = select(Provider)
    if id_especialidad is not None:
        query = query.where(Provider.specialty_id == id_especialidad)
    providers = session.exec(query.order_by(Provider.id)).all()
    return [
        PrestadorRead(id=row.id, nombre_completo=row.full_name, id_especialidad=row.specialty_id)
        for row in providers
    ]


@router.get("/prestadores/{id_prestador}/cupos", response_model=list[CupoRead])
def provider_slots(
    id_prestador: int,
    fecha: date,
    session: Session = Depends(get_session),
) -> list[CupoRead]:
    provider = session.get(Provider, id_prestador)
    if provider is None:
        raise HTTPException(status_code=404, detail="Prestador no encontrado")

    slots = build_daily_slots(id_prestador, fecha)
    blocked = blocked_slots(id_prestador, fecha)
    booked_rows = session.exec(
        select(Appointment).where(
            Appointment.provider_id == id_prestador,
            Appointment.slot_start.in_(slots),
            Appointment.status == "scheduled",
        )
    ).all()
    booked = {row.slot_start for row in booked_rows}

    return [
        CupoRead(
            id_prestador=id_prestador,
            fecha_hora=slot,
            bloqueado=slot in blocked,
            disponible=(slot not in blocked and slot not in booked),
        )
        for slot in slots
    ]
