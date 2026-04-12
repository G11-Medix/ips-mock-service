import pytest
from fastapi.testclient import TestClient

from app.main import app


HEADERS = {"x-api-key": "dev-api-key"}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_specialties_contract(client: TestClient) -> None:
    response = client.get("/api/v1/especialidades", headers=HEADERS)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert {"id", "nombre"} <= set(response.json()[0].keys())


def test_providers_and_slots_contract(client: TestClient) -> None:
    providers = client.get("/api/v1/prestadores?id_especialidad=1", headers=HEADERS)

    assert providers.status_code == 200
    provider = providers.json()[0]
    assert {"id", "nombre_completo", "id_especialidad"} <= set(provider.keys())

    slots = client.get(f"/api/v1/prestadores/{provider['id']}/cupos?fecha=2026-04-01", headers=HEADERS)

    assert slots.status_code == 200
    slot = slots.json()[0]
    assert {"id_prestador", "fecha_hora", "disponible", "bloqueado"} <= set(slot.keys())


def test_ips_and_patient_contract(client: TestClient) -> None:
    ips = client.get("/api/v1/ips/actual", headers=HEADERS)
    patients = client.get("/api/v1/pacientes", headers=HEADERS)

    assert ips.status_code == 200
    assert {"id_ips", "nombre", "estado"} <= set(ips.json().keys())
    assert patients.status_code == 200
    patient = patients.json()[0]

    found = client.get(
        f"/api/v1/pacientes/{patient['tipo_documento']}/{patient['numero_documento']}",
        headers=HEADERS,
    )

    assert found.status_code == 200
    assert {"id_paciente", "tipo_documento", "numero_documento"} <= set(found.json().keys())


def test_appointment_create_cancel_and_reschedule_contract(client: TestClient) -> None:
    patient = client.get("/api/v1/pacientes", headers=HEADERS).json()[0]
    provider = client.get("/api/v1/prestadores?id_especialidad=1", headers=HEADERS).json()[0]
    slots = client.get(
        f"/api/v1/prestadores/{provider['id']}/cupos?fecha=2026-04-01",
        headers=HEADERS,
    ).json()
    available_slots = [slot for slot in slots if slot["disponible"] and not slot["bloqueado"]]

    assert len(available_slots) >= 2

    created = client.post(
        "/api/v1/citas",
        headers=HEADERS,
        json={
            "id_paciente": patient["id_paciente"],
            "id_prestador": provider["id"],
            "fecha_hora_cupo": available_slots[0]["fecha_hora"],
        },
    )

    assert created.status_code == 201
    cita = created.json()
    assert {"id", "id_paciente", "id_prestador", "id_especialidad", "estado"} <= set(cita.keys())

    cancelled = client.patch(
        f"/api/v1/citas/{cita['id']}/cancelar",
        headers=HEADERS,
        json={"motivo": "No puedo asistir"},
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["estado"] == "cancelled"

    created_again = client.post(
        "/api/v1/citas",
        headers=HEADERS,
        json={
            "id_paciente": patient["id_paciente"],
            "id_prestador": provider["id"],
            "fecha_hora_cupo": available_slots[1]["fecha_hora"],
        },
    )
    assert created_again.status_code == 201
    cita_again = created_again.json()

    remaining_slots = client.get(
        f"/api/v1/prestadores/{provider['id']}/cupos?fecha=2026-04-01",
        headers=HEADERS,
    ).json()
    reschedule_target = next(
        slot
        for slot in remaining_slots
        if slot["disponible"] and not slot["bloqueado"] and slot["fecha_hora"] != available_slots[1]["fecha_hora"]
    )

    rescheduled = client.patch(
        f"/api/v1/citas/{cita_again['id']}/reprogramar",
        headers=HEADERS,
        json={"nueva_fecha_hora_cupo": reschedule_target["fecha_hora"]},
    )

    assert rescheduled.status_code == 200
    assert rescheduled.json()["fecha_hora_cupo"] == reschedule_target["fecha_hora"]
