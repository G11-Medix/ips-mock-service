import pytest
from fastapi.testclient import TestClient

from app.main import app


FHIR_HEADERS = {
    "Accept": "application/fhir+json",
    "Content-Type": "application/fhir+json",
}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_legacy_routes_are_not_mounted(client: TestClient) -> None:
    response = client.get("/api/v1/prestadores")

    assert response.status_code == 404


def test_organization_patient_provider_and_slot_contracts_are_fhir(client: TestClient) -> None:
    organizations = client.get("/fhir/Organization", headers=FHIR_HEADERS)

    assert organizations.status_code == 200
    organization_bundle = organizations.json()
    assert organization_bundle["resourceType"] == "Bundle"
    organization = organization_bundle["entry"][0]["resource"]
    assert organization["resourceType"] == "Organization"
    assert {"id", "identifier", "name"} <= set(organization.keys())

    patients = client.get("/fhir/Patient", headers=FHIR_HEADERS)

    assert patients.status_code == 200
    patient_bundle = patients.json()
    patient = patient_bundle["entry"][0]["resource"]
    assert patient["resourceType"] == "Patient"
    assert {"id", "identifier", "name"} <= set(patient.keys())

    roles = client.get("/fhir/PractitionerRole?specialty=335", headers=FHIR_HEADERS)

    assert roles.status_code == 200
    role_bundle = roles.json()
    role = role_bundle["entry"][0]["resource"]
    assert role["resourceType"] == "PractitionerRole"
    assert role["specialty"][0]["coding"][0]["code"] == "335"

    provider_reference = role["practitioner"]["reference"]
    provider_id = provider_reference.split("/", 1)[1]
    slots = client.get(
        f"/fhir/Slot?schedule=Schedule/{provider_id}&start=2026-04-01",
        headers=FHIR_HEADERS,
    )

    assert slots.status_code == 200
