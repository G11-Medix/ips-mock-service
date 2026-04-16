import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


FHIR_HEADERS = {
    "Accept": "application/fhir+json",
    "Content-Type": "application/fhir+json",
}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _smart_headers(
    *,
    patient_id: int | str = 1,
    scope: str = "patient/Slot.read patient/Appointment.read patient/Appointment.write",
) -> dict[str, str]:
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "smart-user-1",
            "aud": settings.smart_audience,
            "iss": settings.smart_issuer or f"{settings.supabase_url.rstrip('/')}/auth/v1",
            "patient_id": str(patient_id),
            "scope": scope,
        },
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    return {**FHIR_HEADERS, "Authorization": f"Bearer {token}"}


def _first_available_slot(client: TestClient, provider_id: int, target_date: str, headers: dict[str, str]) -> str:
    slots = client.get(
        "/fhir/Slot",
        headers=headers,
        params={"schedule": f"Schedule/{provider_id}", "start": target_date},
    )
    assert slots.status_code == 200
    bundle = slots.json()
    return next(
        entry["resource"]["start"]
        for entry in bundle["entry"]
        if entry["resource"]["status"] == "free"
    )


def _first_patient(client: TestClient) -> dict:
    bundle = client.get("/fhir/Patient", headers=FHIR_HEADERS).json()
    return bundle["entry"][0]["resource"]


def _provider_role_by_specialty(client: TestClient, specialty_code: str) -> dict:
    bundle = client.get(f"/fhir/PractitionerRole?specialty={specialty_code}", headers=FHIR_HEADERS).json()
    return bundle["entry"][0]["resource"]


def test_metadata_and_patient_search_are_fhir() -> None:
    with TestClient(app) as client:
        smart_config = client.get("/.well-known/smart-configuration")
        assert smart_config.status_code == 200
        smart_body = smart_config.json()
        assert smart_body["authorization_endpoint"].endswith("/auth/v1/authorize")
        assert smart_body["token_endpoint"].endswith("/auth/v1/token")
        assert "launch-standalone" in smart_body["capabilities"]
        assert "permission-patient" in smart_body["capabilities"]

        metadata = client.get("/fhir/metadata", headers=FHIR_HEADERS)
        assert metadata.status_code == 200
        assert metadata.headers["content-type"].startswith("application/fhir+json")
        assert metadata.json()["resourceType"] == "CapabilityStatement"

        patient = _first_patient(client)
        search = client.get(
            "/fhir/Patient",
            headers=FHIR_HEADERS,
            params={"identifier": f"{patient['identifier'][0]['system']}|{patient['identifier'][0]['value']}"},
        )

        assert search.status_code == 200
        body = search.json()
        assert body["resourceType"] == "Bundle"
        assert body["type"] == "searchset"
        assert body["entry"][0]["resource"]["resourceType"] == "Patient"


def test_slot_and_appointment_require_smart_token_and_scopes(client: TestClient) -> None:
    no_auth = client.get(
        "/fhir/Slot",
        headers=FHIR_HEADERS,
        params={"schedule": "Schedule/1", "start": "2026-04-01"},
    )
    assert no_auth.status_code == 401
    assert no_auth.json()["resourceType"] == "OperationOutcome"

    wrong_scope = client.get(
        "/fhir/Slot",
        headers=_smart_headers(scope="patient/Appointment.read"),
        params={"schedule": "Schedule/1", "start": "2026-04-01"},
    )
    assert wrong_scope.status_code == 403
    assert wrong_scope.json()["issue"][0]["code"] == "forbidden"


def test_appointment_create_cancel_and_reschedule_update_slot_state(client: TestClient) -> None:
    patient = _first_patient(client)
    role = _provider_role_by_specialty(client, "335")
    provider_id = int(role["practitioner"]["reference"].split("/", 1)[1])

    auth_headers = _smart_headers(patient_id=patient["id"])
    first_start = _first_available_slot(client, provider_id, "2026-04-01", auth_headers)
    create_payload = {
        "resourceType": "Appointment",
        "status": "booked",
        "specialty": [
            {
                "coding": [
                    {
                        "system": "urn:medix:specialty",
                        "code": "335",
                        "display": "Pediatria",
                    }
                ],
                "text": "Pediatria",
            }
        ],
        "slot": [{"reference": f"Slot/{provider_id}-{first_start}"}],
        "participant": [
            {"actor": {"reference": f"Patient/{patient['id']}"}, "status": "accepted"},
            {"actor": {"reference": f"Practitioner/{provider_id}"}, "status": "accepted"},
        ],
    }

    created = client.post("/fhir/Appointment", headers=auth_headers, json=create_payload)
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["resourceType"] == "Appointment"
    assert created_body["status"] == "booked"
    assert created_body["specialty"][0]["coding"][0]["code"] == "335"

    busy_slots = client.get(
        "/fhir/Slot",
        headers=auth_headers,
        params={"schedule": f"Schedule/{provider_id}", "start": "2026-04-01", "status": "busy"},
    ).json()
    assert any(entry["resource"]["start"] == first_start for entry in busy_slots["entry"])

    second_start = next(
        entry["resource"]["start"]
        for entry in client.get(
            "/fhir/Slot",
            headers=auth_headers,
            params={"schedule": f"Schedule/{provider_id}", "start": "2026-04-01"},
        ).json()["entry"]
        if entry["resource"]["status"] == "free" and entry["resource"]["start"] != first_start
    )

    rescheduled = client.patch(
        f"/fhir/Appointment/{created_body['id']}",
        headers=auth_headers,
        json={"slot": [{"reference": f"Slot/{provider_id}-{second_start}"}]},
    )
    assert rescheduled.status_code == 200
    assert rescheduled.json()["start"] == second_start

    busy_after_reschedule = client.get(
        "/fhir/Slot",
        headers=auth_headers,
        params={"schedule": f"Schedule/{provider_id}", "start": "2026-04-01"},
    ).json()["entry"]
    old_slot = next(entry["resource"] for entry in busy_after_reschedule if entry["resource"]["start"] == first_start)
    new_slot = next(entry["resource"] for entry in busy_after_reschedule if entry["resource"]["start"] == second_start)
    assert old_slot["status"] == "free"
    assert new_slot["status"] == "busy"

    cancelled = client.patch(
        f"/fhir/Appointment/{created_body['id']}",
        headers=auth_headers,
        json={"status": "cancelled", "cancelationReason": {"text": "No puedo asistir"}},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    final_slots = client.get(
        "/fhir/Slot",
        headers=auth_headers,
        params={"schedule": f"Schedule/{provider_id}", "start": "2026-04-01"},
    ).json()["entry"]
    released_slot = next(entry["resource"] for entry in final_slots if entry["resource"]["start"] == second_start)
    assert released_slot["status"] == "free"


def test_appointment_forbidden_when_patient_claim_does_not_match(client: TestClient) -> None:
    patient = _first_patient(client)
    role = _provider_role_by_specialty(client, "335")
    provider_id = int(role["practitioner"]["reference"].split("/", 1)[1])
    first_start = _first_available_slot(client, provider_id, "2026-04-01", _smart_headers())

    response = client.post(
        "/fhir/Appointment",
        headers=_smart_headers(patient_id=int(patient["id"]) + 999),
        json={
            "resourceType": "Appointment",
            "status": "booked",
            "specialty": [{"coding": [{"system": "urn:medix:specialty", "code": "335"}]}],
            "slot": [{"reference": f"Slot/{provider_id}-{first_start}"}],
            "participant": [
                {"actor": {"reference": f"Patient/{patient['id']}"}, "status": "accepted"},
                {"actor": {"reference": f"Practitioner/{provider_id}"}, "status": "accepted"},
            ],
        },
    )

    assert response.status_code == 403
    assert response.json()["resourceType"] == "OperationOutcome"
    assert response.json()["issue"][0]["code"] == "forbidden"


def test_fhir_errors_return_operation_outcome(client: TestClient) -> None:
    response = client.get("/fhir/Patient/999999", headers=FHIR_HEADERS)

    assert response.status_code == 404
    body = response.json()
    assert body["resourceType"] == "OperationOutcome"
    assert body["issue"][0]["code"] == "not-found"
