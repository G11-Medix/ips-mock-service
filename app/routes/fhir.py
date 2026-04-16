from __future__ import annotations

from datetime import date, datetime

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.entities import Appointment, IPS, Paciente, Provider, Specialty
from app.services.appointments import ensure_patient_exists, ensure_provider_exists, list_appointments, validate_slot
from app.services.fhir import (
    FHIR_JSON_MEDIA_TYPE,
    appointment_cancel_reason,
    appointment_resource,
    appointment_status_from_fhir,
    capability_statement,
    date_matches_filter,
    extract_reference_id,
    find_participant_reference,
    operation_outcome,
    organization_resource,
    parse_identifier_query,
    parse_slot_id,
    patient_resource,
    practitioner_resource,
    practitioner_role_resource,
    schedule_resource,
    slot_resource,
    specialty_code_from_resource,
    to_bundle,
)
from app.services.slots import blocked_slots, build_daily_slots, is_slot_available

router = APIRouter(prefix="/fhir", tags=["FHIR"])


def fhir_json(payload: dict, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=payload, status_code=status_code, media_type=FHIR_JSON_MEDIA_TYPE)


def _organization_id(session: Session) -> int:
    organization = session.exec(select(IPS).order_by(IPS.id_ips)).first()
    if organization is None or organization.id_ips is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Organization no encontrada"))
    return int(organization.id_ips)


@router.get("/metadata")
def metadata(request: Request) -> JSONResponse:
    return fhir_json(capability_statement(str(request.base_url).rstrip("/")))


@router.get("/Patient")
def search_patient(
    request: Request,
    identifier: str | None = None,
    session: Session = Depends(get_session),
) -> JSONResponse:
    query = select(Paciente)
    if identifier:
        tipo_documento, numero_documento = parse_identifier_query(identifier)
        query = query.where(Paciente.numero_documento == numero_documento)
        if tipo_documento:
            query = query.where(Paciente.tipo_documento == tipo_documento)

    patients = session.exec(query.order_by(Paciente.id_paciente)).all()
    resources = [patient_resource(row) for row in patients]
    return fhir_json(to_bundle("Patient", resources, str(request.base_url).rstrip("/")))


@router.get("/Patient/{patient_id}")
def get_patient(patient_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    patient = session.get(Paciente, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Patient no encontrado"))
    return fhir_json(patient_resource(patient))


@router.get("/Organization/{organization_id}")
def get_organization(organization_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    organization = session.get(IPS, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Organization no encontrada"))
    return fhir_json(organization_resource(organization))


@router.get("/Organization")
def search_organization(
    request: Request,
    identifier: str | None = None,
    session: Session = Depends(get_session),
) -> JSONResponse:
    query = select(IPS)
    if identifier:
        _, value = parse_identifier_query(identifier)
        query = query.where(IPS.nit == value)

    organizations = session.exec(query.order_by(IPS.id_ips)).all()
    resources = [organization_resource(row) for row in organizations]
    return fhir_json(to_bundle("Organization", resources, str(request.base_url).rstrip("/")))


@router.get("/Practitioner/{practitioner_id}")
def get_practitioner(practitioner_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    practitioner = session.get(Provider, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Practitioner no encontrado"))
    return fhir_json(practitioner_resource(practitioner))


@router.get("/PractitionerRole")
def search_practitioner_roles(
    request: Request,
    organization: str | None = None,
    specialty: str | None = None,
    practitioner: str | None = None,
    session: Session = Depends(get_session),
) -> JSONResponse:
    organization_id = extract_reference_id(organization, "Organization")
    practitioner_id = extract_reference_id(practitioner, "Practitioner")
    specialty_code = specialty if specialty is not None else None
    resolved_organization_id = int(organization_id) if organization_id is not None else _organization_id(session)
    specialty_by_id = {int(item.id): item for item in session.exec(select(Specialty)).all()}
    providers = session.exec(select(Provider).order_by(Provider.id)).all()

    resources = []
    for provider_row in providers:
        if practitioner_id is not None and int(practitioner_id) != provider_row.id:
            continue
        specialty_row = specialty_by_id[int(provider_row.specialty_id)]
        if specialty_code is not None and specialty_code != specialty_row.codigo_reps:
            continue
        if organization_id is not None and session.get(IPS, resolved_organization_id) is None:
            continue
        resources.append(practitioner_role_resource(provider_row, specialty_row, resolved_organization_id))

    return fhir_json(to_bundle("PractitionerRole", resources, str(request.base_url).rstrip("/")))


@router.get("/Schedule")
def search_schedule(
    request: Request,
    actor: str | None = None,
    session: Session = Depends(get_session),
) -> JSONResponse:
    actor_id = extract_reference_id(actor, "Practitioner") or extract_reference_id(actor, "PractitionerRole")
    organization_id = _organization_id(session)
    specialty_by_id = {int(item.id): item for item in session.exec(select(Specialty)).all()}
    providers = session.exec(select(Provider).order_by(Provider.id)).all()
    resources = []
    for provider in providers:
        if actor_id is not None and int(actor_id) != provider.id:
            continue
        resources.append(schedule_resource(provider, specialty_by_id[int(provider.specialty_id)], organization_id))
    return fhir_json(to_bundle("Schedule", resources, str(request.base_url).rstrip("/")))


@router.get("/Slot")
def search_slots(
    request: Request,
    schedule: str | None = None,
    start: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
) -> JSONResponse:
    schedule_id = extract_reference_id(schedule, "Schedule")
    if schedule_id is None:
        raise HTTPException(status_code=400, detail=operation_outcome("required", "schedule es obligatorio"))

    provider = ensure_provider_exists(session, int(schedule_id))
    specialty = session.get(Specialty, provider.specialty_id)
    if specialty is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Specialty no encontrada"))

    target_date = date.fromisoformat(start) if start else date.today()
    slots = build_daily_slots(provider.id, target_date)
    blocked = blocked_slots(provider.id, target_date)
    booked_rows = session.exec(
        select(Appointment).where(
            Appointment.provider_id == provider.id,
            Appointment.slot_start.in_(slots),
            Appointment.status == "scheduled",
        )
    ).all()
    booked = {row.slot_start for row in booked_rows}

    resources = []
    organization_id = _organization_id(session)
    for slot_start in slots:
        slot_status = "busy-unavailable" if slot_start in blocked else "busy" if slot_start in booked else "free"
        if status is not None and status != slot_status:
            continue
        resources.append(slot_resource(provider, specialty, organization_id, slot_start, slot_status))
    return fhir_json(to_bundle("Slot", resources, str(request.base_url).rstrip("/")))


@router.get("/Appointment")
def search_appointments(
    request: Request,
    patient: str | None = None,
    date: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
) -> JSONResponse:
    patient_id = extract_reference_id(patient, "Patient")
    db_status = appointment_status_from_fhir(status) if status else None
    rows = list_appointments(
        session,
        patient_id=int(patient_id) if patient_id is not None else None,
        from_date=None,
        to_date=None,
    )
    specialty_by_id = {int(item.id): item for item in session.exec(select(Specialty)).all()}
    provider_by_id = {int(item.id): item.full_name for item in session.exec(select(Provider)).all()}
    resources = []
    for row in rows:
        if db_status is not None and row.status != db_status:
            continue
        if not date_matches_filter(row.slot_start, date):
            continue
        resources.append(
            appointment_resource(
                row,
                provider_name=provider_by_id[int(row.provider_id)],
                specialty_name=specialty_by_id[int(row.specialty_id)].name,
                specialty_codigo_reps=specialty_by_id[int(row.specialty_id)].codigo_reps,
            )
        )
    return fhir_json(to_bundle("Appointment", resources, str(request.base_url).rstrip("/")))


@router.get("/Appointment/{appointment_id}")
def get_appointment(
    appointment_id: int,
    session: Session = Depends(get_session),
) -> JSONResponse:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Appointment no encontrada"))
    provider = ensure_provider_exists(session, appointment.provider_id)
    specialty = session.get(Specialty, appointment.specialty_id)
    if specialty is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Specialty no encontrada"))
    return fhir_json(appointment_resource(appointment, provider.full_name, specialty.name, specialty.codigo_reps))


@router.post("/Appointment", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    request: Request,
    session: Session = Depends(get_session),
) -> JSONResponse:
    payload = await request.json()
    patient_id = find_participant_reference(payload, "Patient")
    practitioner_id = find_participant_reference(payload, "Practitioner")
    slot_references = payload.get("slot") or []
    slot_reference = slot_references[0]["reference"] if slot_references else None
    raw_slot_id = extract_reference_id(slot_reference, "Slot")
    if patient_id is None or raw_slot_id is None:
        raise HTTPException(status_code=400, detail=operation_outcome("invalid", "Appointment incompleta"))
    if str(payload.get("status") or "").lower() != "booked":
        raise HTTPException(status_code=400, detail=operation_outcome("value", "Appointment.status debe ser booked"))

    provider_id_from_slot, slot_start = parse_slot_id(raw_slot_id)
    provider_id = int(practitioner_id) if practitioner_id is not None else provider_id_from_slot
    ensure_patient_exists(session, int(patient_id))
    provider = ensure_provider_exists(session, provider_id)
    validate_slot(session, provider.id, slot_start)
    specialty = session.get(Specialty, provider.specialty_id)
    if specialty is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Specialty no encontrada"))
    requested_specialty_code = specialty_code_from_resource(payload)
    if requested_specialty_code is not None and requested_specialty_code != specialty.codigo_reps:
        raise HTTPException(
            status_code=400,
            detail=operation_outcome("value", "Appointment.specialty no coincide con la especialidad del prestador"),
        )

    appointment = Appointment(
        patient_id=int(patient_id),
        provider_id=provider.id,
        specialty_id=provider.specialty_id,
        slot_start=slot_start,
        status=appointment_status_from_fhir(str(payload.get("status") or "booked")),
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return fhir_json(
        appointment_resource(appointment, provider.full_name, specialty.name, specialty.codigo_reps),
        status_code=201,
    )


@router.patch("/Appointment/{appointment_id}")
@router.put("/Appointment/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> JSONResponse:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Appointment no encontrada"))

    payload = await request.json()
    requested_status = str(payload.get("status") or "").lower()
    if requested_status == "cancelled":
        if appointment.status == "cancelled":
            raise HTTPException(status_code=409, detail=operation_outcome("conflict", "La cita ya fue cancelada"))
        appointment.status = "cancelled"
        appointment.cancel_reason = appointment_cancel_reason(payload)
    else:
        slot_references = payload.get("slot") or []
        slot_reference = slot_references[0]["reference"] if slot_references else None
        raw_slot_id = extract_reference_id(slot_reference, "Slot")
        if raw_slot_id is None:
            raise HTTPException(status_code=400, detail=operation_outcome("invalid", "slot es obligatorio"))
        provider_id, slot_start = parse_slot_id(raw_slot_id)
        provider = ensure_provider_exists(session, provider_id)
        validate_slot(session, provider.id, slot_start, appointment_id=appointment.id)
        specialty = session.get(Specialty, provider.specialty_id)
        if specialty is None:
            raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Specialty no encontrada"))
        requested_specialty_code = specialty_code_from_resource(payload)
        if requested_specialty_code is not None and requested_specialty_code != specialty.codigo_reps:
            raise HTTPException(
                status_code=400,
                detail=operation_outcome("value", "Appointment.specialty no coincide con la especialidad del prestador"),
            )
        appointment.provider_id = provider.id
        appointment.specialty_id = provider.specialty_id
        appointment.slot_start = slot_start
        appointment.status = "scheduled"
        appointment.cancel_reason = None

    appointment.updated_at = datetime.utcnow()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    provider = ensure_provider_exists(session, appointment.provider_id)
    specialty = session.get(Specialty, appointment.specialty_id)
    if specialty is None:
        raise HTTPException(status_code=404, detail=operation_outcome("not-found", "Specialty no encontrada"))
    return fhir_json(appointment_resource(appointment, provider.full_name, specialty.name, specialty.codigo_reps))


@router.get("/health")
def health() -> Response:
    return Response(status_code=204)
