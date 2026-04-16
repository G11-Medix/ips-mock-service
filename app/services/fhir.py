from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.models.entities import Appointment, IPS, Paciente, Provider, Specialty


FHIR_JSON_MEDIA_TYPE = "application/fhir+json"
SPECIALTY_SYSTEM = "urn:medix:specialty"


def operation_outcome(code: str, diagnostics: str, severity: str = "error") -> dict[str, Any]:
    return {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": severity,
                "code": code,
                "diagnostics": diagnostics,
            }
        ],
    }


def capability_statement(base_url: str) -> dict[str, Any]:
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": datetime.utcnow().isoformat(),
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Organization", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Practitioner", "interaction": [{"code": "read"}]},
                    {"type": "PractitionerRole", "interaction": [{"code": "search-type"}]},
                    {"type": "Schedule", "interaction": [{"code": "search-type"}]},
                    {"type": "Slot", "interaction": [{"code": "search-type"}]},
                    {
                        "type": "Appointment",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"},
                            {"code": "create"},
                            {"code": "update"},
                            {"code": "patch"},
                        ],
                    },
                ],
            }
        ],
        "implementation": {
            "description": "Medix IPS Mock FHIR R4",
            "url": f"{base_url.rstrip('/')}/fhir",
        },
    }


def to_bundle(resource_type: str, resources: list[dict[str, Any]], base_url: str) -> dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [
            {
                "fullUrl": f"{base_url.rstrip('/')}/fhir/{resource_type}/{resource['id']}",
                "resource": resource,
                "search": {"mode": "match"},
            }
            for resource in resources
        ],
    }


def document_identifier_system(tipo_documento: str) -> str:
    normalized = str(tipo_documento or "").strip().lower() or "unknown"
    return f"urn:medix:document:{normalized}"


def parse_identifier_query(value: str) -> tuple[str | None, str]:
    if "|" not in value:
        return None, value
    raw_type, number = value.split("|", 1)
    tipo = raw_type.rsplit(":", 1)[-1].upper()
    return (tipo or None), number


def specialty_coding(codigo_reps: str | None, specialty_name: str) -> dict[str, Any]:
    concept: dict[str, Any] = {"text": specialty_name}
    if codigo_reps is not None:
        concept["coding"] = [
            {
                "system": SPECIALTY_SYSTEM,
                "code": str(codigo_reps),
                "display": specialty_name,
            }
        ]
    return concept


def patient_resource(patient: Paciente) -> dict[str, Any]:
    return {
        "resourceType": "Patient",
        "id": str(patient.id_paciente),
        "active": str(patient.estado or "").lower() == "activo",
        "identifier": [
            {
                "system": document_identifier_system(patient.tipo_documento),
                "value": patient.numero_documento,
                "type": {"text": patient.tipo_documento},
            }
        ],
        "name": [
            {
                "family": patient.apellidos,
                "given": [patient.nombres],
                "text": f"{patient.nombres} {patient.apellidos}",
            }
        ],
        "telecom": [
            *(
                [{"system": "phone", "value": patient.telefono, "use": "mobile"}]
                if patient.telefono
                else []
            ),
            *(
                [{"system": "email", "value": patient.correo}]
                if patient.correo
                else []
            ),
        ],
        "birthDate": patient.fecha_nacimiento.isoformat(),
    }


def organization_resource(ips: IPS) -> dict[str, Any]:
    return {
        "resourceType": "Organization",
        "id": str(ips.id_ips),
        "active": str(ips.estado or "").lower() == "activo",
        "identifier": [{"system": "urn:medix:nit", "value": ips.nit}],
        "name": ips.nombre,
        "telecom": (
            [{"system": "phone", "value": ips.telefono}]
            if ips.telefono
            else []
        ),
        "address": (
            [{"text": ips.direccion}]
            if ips.direccion
            else []
        ),
    }


def practitioner_resource(provider: Provider) -> dict[str, Any]:
    given_names = [part for part in provider.full_name.split(" ") if part]
    family = given_names.pop() if len(given_names) > 1 else provider.full_name
    return {
        "resourceType": "Practitioner",
        "id": str(provider.id),
        "active": True,
        "name": [
            {
                "family": family,
                "given": given_names or [provider.full_name],
                "text": provider.full_name,
            }
        ],
    }


def practitioner_role_resource(provider: Provider, specialty: Specialty, organization_id: int) -> dict[str, Any]:
    return {
        "resourceType": "PractitionerRole",
        "id": str(provider.id),
        "active": True,
        "practitioner": {
            "reference": f"Practitioner/{provider.id}",
            "display": provider.full_name,
        },
        "organization": {"reference": f"Organization/{organization_id}"},
        "specialty": [specialty_coding(specialty.codigo_reps, specialty.name)],
    }


def schedule_resource(provider: Provider, specialty: Specialty, organization_id: int) -> dict[str, Any]:
    return {
        "resourceType": "Schedule",
        "id": str(provider.id),
        "active": True,
        "actor": [
            {
                "reference": f"Practitioner/{provider.id}",
                "display": provider.full_name,
            },
            {"reference": f"PractitionerRole/{provider.id}"},
            {"reference": f"Organization/{organization_id}"},
        ],
        "serviceType": [specialty_coding(specialty.codigo_reps, specialty.name)],
    }


def slot_id(provider_id: int, slot_start: datetime) -> str:
    return f"{provider_id}-{slot_start.isoformat()}"


def parse_slot_id(raw_slot_id: str) -> tuple[int, datetime]:
    provider_id_raw, slot_start_raw = raw_slot_id.split("-", 1)
    return int(provider_id_raw), datetime.fromisoformat(slot_start_raw)


def slot_resource(
    provider: Provider,
    specialty: Specialty,
    organization_id: int,
    slot_start: datetime,
    status: str,
) -> dict[str, Any]:
    slot_end = slot_start + timedelta(minutes=30)
    schedule = schedule_resource(provider, specialty, organization_id)
    return {
        "resourceType": "Slot",
        "id": slot_id(int(provider.id), slot_start),
        "schedule": {"reference": f"Schedule/{schedule['id']}"},
        "status": status,
        "start": slot_start.isoformat(),
        "end": slot_end.isoformat(),
    }


def appointment_resource(
    appointment: Appointment,
    provider_name: str,
    specialty_name: str,
    specialty_codigo_reps: str | None,
) -> dict[str, Any]:
    status = "booked" if appointment.status == "scheduled" else "cancelled"
    resource: dict[str, Any] = {
        "resourceType": "Appointment",
        "id": str(appointment.id),
        "status": status,
        "meta": {"lastUpdated": appointment.updated_at.isoformat()},
        "specialty": [specialty_coding(specialty_codigo_reps, specialty_name)],
        "slot": [{"reference": f"Slot/{slot_id(int(appointment.provider_id), appointment.slot_start)}"}],
        "participant": [
            {
                "actor": {"reference": f"Patient/{appointment.patient_id}"},
                "status": "accepted",
            },
            {
                "actor": {
                    "reference": f"Practitioner/{appointment.provider_id}",
                    "display": provider_name,
                },
                "status": "accepted",
            },
        ],
        "created": appointment.created_at.isoformat(),
        "start": appointment.slot_start.isoformat(),
        "end": (appointment.slot_start + timedelta(minutes=30)).isoformat(),
    }
    if appointment.cancel_reason:
        resource["cancelationReason"] = {"text": appointment.cancel_reason}
    return resource


def appointment_status_from_fhir(status: str) -> str:
    normalized = str(status or "").lower()
    if normalized in {"booked", "pending", "arrived", "fulfilled"}:
        return "scheduled"
    if normalized == "cancelled":
        return "cancelled"
    return "scheduled"


def appointment_status_to_fhir(status: str) -> str:
    return "booked" if str(status or "").lower() == "scheduled" else "cancelled"


def extract_reference_id(reference: str | None, resource_type: str) -> str | None:
    if not reference:
        return None
    prefix = f"{resource_type}/"
    if reference.startswith(prefix):
        return reference[len(prefix):]
    if "/" not in reference:
        return reference
    return None


def find_participant_reference(resource: dict[str, Any], resource_type: str) -> str | None:
    for participant in resource.get("participant", []):
        actor = participant.get("actor") or {}
        reference_id = extract_reference_id(actor.get("reference"), resource_type)
        if reference_id is not None:
            return reference_id
    return None


def specialty_code_from_resource(resource: dict[str, Any]) -> str | None:
    for item in resource.get("specialty", []):
        for coding in item.get("coding", []):
            if coding.get("system") == SPECIALTY_SYSTEM and coding.get("code"):
                return str(coding["code"])
    return None


def appointment_cancel_reason(resource: dict[str, Any]) -> str | None:
    reason = resource.get("cancelationReason") or resource.get("cancellationReason")
    if isinstance(reason, dict):
        text = reason.get("text")
        return str(text) if text else None
    return None


def date_matches_filter(slot_start: datetime, raw_date: str | None) -> bool:
    if not raw_date:
        return True
    return slot_start.date() == date.fromisoformat(raw_date)
