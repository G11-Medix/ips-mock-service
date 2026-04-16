# Mock IPS para integraciones de agenda

Servicio mock parametrizable por instancia IPS para simular integraciones con sistemas de agendamiento de citas medicas usando HL7 FHIR R4.

## Stack
- Python 3.11
- FastAPI
- SQLModel + SQLite
- Docker + Docker Compose

## Ejecutar con Docker Compose (5 IPS)
```bash
docker compose up --build
```

Instancias:
- `ips_santa_fe`: `http://localhost:4011`
- `ips_country`: `http://localhost:4012`
- `ips_clinica_colombia`: `http://localhost:4013`
- `ips_san_ignacio`: `http://localhost:4014`
- `ips_mederi`: `http://localhost:4015`

Cada instancia usa su propia base SQLite en:
- `./data/ips-fsf/ips.db`
- `./data/ips-cly/ips.db`
- `./data/ips-cuc/ips.db`
- `./data/ips-hsi/ips.db`
- `./data/ips-med/ips.db`

## Seeder inicial
El seeder crea datos deterministas por instancia:
- IPS principal de la instancia (`IPS_NAME`, `IPS_CODE`, `IPS_NIT`)
- Pacientes propios por IPS
- Especialidades y prestadores por IPS
- Una cita demo inicial para pruebas del flujo


## Nota de datos
Por defecto el servicio reinicia y reseed la base al iniciar (`RESET_DB_ON_STARTUP=true`), ideal para pruebas repetibles.

## Contrato FHIR
- El mock expone solo endpoints FHIR bajo `/fhir`.
- La IPS se consulta con `GET /fhir/Organization`.
- Los pacientes se consultan con `GET /fhir/Patient`.
- Los prestadores por especialidad se consultan con `GET /fhir/PractitionerRole?specialty={codigo_reps}`.
- La agenda de un prestador se consulta con `GET /fhir/Slot?schedule=Schedule/{id_prestador}&start=YYYY-MM-DD`.
- La gestion de citas se hace con `Appointment` en `GET /fhir/Appointment`, `POST /fhir/Appointment` y `PATCH /fhir/Appointment/{id}`.

## Especialidades con codigo REPS
- El mock publica `codigo_reps` en los `CodeableConcept` de especialidad para `PractitionerRole`, `Schedule` y `Appointment`.
- Hoy estan mapeadas estas especialidades: Medicina General `101`, Cardiologia `302`, Dermatologia `312`, Gastroenterologia `315`, Ginecobstetricia `318`, Neurologia `329`, Oftalmologia `330`, Ortopedia `331`, Pediatria `335` y Psicologia `342`.
