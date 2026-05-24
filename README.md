# IPS Mock Service

Servicio mock parametrizable por instancia IPS para simular integraciones con sistemas de agendamiento de citas médicas usando HL7 FHIR R4. Este repositorio permite validar contratos de interoperabilidad dentro del proyecto de grado sin depender directamente de sistemas reales de instituciones prestadoras de salud.

## Descripción general

Este repositorio implementa una API mock para instituciones prestadoras de salud (IPS), orientada a exponer recursos FHIR relacionados con organizaciones, pacientes, prestadores, agendas, horarios disponibles y citas médicas.

El servicio pertenece al ecosistema Medix y cumple el rol de simulador de integración para sistemas externos de agenda médica. Dentro de la arquitectura general del proyecto, permite probar flujos de consulta, creación, cancelación y reagendamiento de citas sobre endpoints compatibles con HL7 FHIR R4.

El mock puede ejecutarse como una única instancia local o mediante Docker Compose con varias IPS configuradas, cada una con datos determinísticos y una base SQLite independiente.

## Tecnologías utilizadas

- Lenguaje: Python 3.11
- Framework: FastAPI
- Servidor ASGI: Uvicorn
- Base de datos: SQLite
- ORM/modelado de datos: SQLModel
- Configuración: Pydantic Settings
- Pruebas: Pytest, FastAPI TestClient, HTTPX
- Contenedores: Docker, Docker Compose
- Estándar de interoperabilidad: HL7 FHIR R4
- Seguridad/configuración SMART: endpoints de descubrimiento SMART on FHIR y parámetros compatibles con Supabase Auth
- Herramientas: Bruno para colección de peticiones HTTP

## Arquitectura del repositorio

```bash
/
├── app/
│   ├── db/
│   ├── models/
│   ├── routes/
│   ├── schemas/
│   ├── security/
│   ├── services/
│   ├── config.py
│   └── main.py
├── bruno-ips-mock-service/
├── data/
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

- `app/`: contiene el código fuente principal de la API.
- `app/main.py`: inicializa FastAPI, registra routers y ejecuta la creación/seed de base de datos al iniciar.
- `app/config.py`: define la configuración del servicio mediante variables de entorno.
- `app/db/`: configura la conexión SQLite y las sesiones de base de datos.
- `app/models/`: define las entidades persistidas con SQLModel.
- `app/routes/`: expone los endpoints FHIR y SMART on FHIR.
- `app/security/`: contiene utilidades relacionadas con la configuración SMART.
- `app/services/`: implementa lógica de negocio, transformación a recursos FHIR, seeder, slots y citas.
- `bruno-ips-mock-service/`: colección Bruno con peticiones para probar discovery, organizaciones, pacientes, prestadores, slots y citas.
- `data/`: almacena bases SQLite locales por instancia IPS cuando se ejecuta con Docker Compose.
- `tests/`: contiene pruebas automatizadas de contratos FHIR.
- `.env.example`: ejemplo de variables de entorno soportadas.
- `Dockerfile`: define la imagen del servicio FastAPI.
- `docker-compose.yml`: levanta múltiples instancias mock de IPS.
- `requirements.txt`: lista dependencias Python del proyecto.

## Requisitos previos

- Python 3.11 o superior.
- Gestor de paquetes `pip`.
- Docker y Docker Compose, si se desea ejecutar el entorno multi-IPS.
- Variables de entorno definidas en `.env` o mediante Docker Compose, según el modo de ejecución.
- Bruno, opcional, para ejecutar la colección de peticiones HTTP incluida.

## Instalación

```bash
git clone https://github.com/G11-Medix/ips-mock-service.git
cd ips-mock-service
```

Se recomienda crear y activar un entorno virtual antes de instalar dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables de entorno

El repositorio incluye un archivo `.env.example` con las variables soportadas por la aplicación:

```env
IPS_NAME=IPS Demo
IPS_SLUG=ips-demo
IPS_CODE=IPS-DEMO
IPS_NIT=900000000-0
TIMEZONE=America/Bogota
PORT=4011
DB_PATH=./data/ips.db
RESET_DB_ON_STARTUP=true
SUPABASE_URL=http://localhost:54321
SUPABASE_JWT_SECRET=valor-generico-seguro
SMART_AUDIENCE=authenticated
SMART_ISSUER=http://localhost:54321/auth/v1
SMART_PATIENT_CLAIM=patient_id
```

No se deben versionar credenciales reales. Los valores sensibles, como `SUPABASE_JWT_SECRET`, deben configurarse con valores seguros en cada entorno.

En `docker-compose.yml` también aparece la variable `API_KEY`, pero no se identificó su uso directo en la configuración actual de la aplicación. Su necesidad debe ser validada por el equipo de desarrollo.

## Ejecución local

Para ejecutar una instancia local directamente con Python:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4011 --reload
```

La API quedará disponible en:

```text
http://localhost:4011
```

Para ejecutar el entorno con Docker Compose:

```bash
docker compose up --build
```

Instancias configuradas:

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

Por defecto, el servicio reinicia y vuelve a sembrar la base al iniciar cuando `RESET_DB_ON_STARTUP=true`, lo cual facilita pruebas repetibles.

## Pruebas

Las pruebas automatizadas se ejecutan con Pytest:

```bash
pytest
```

Las pruebas actuales validan que los endpoints principales respondan con recursos FHIR, que las rutas legacy no estén montadas y que los flujos de creación, cancelación y reagendamiento de citas actualicen correctamente el estado de los slots.

## Uso general

El servicio expone endpoints FHIR bajo el prefijo `/fhir` y un endpoint de discovery SMART on FHIR.

Endpoints principales:

- `GET /.well-known/smart-configuration`: configuración SMART on FHIR.
- `GET /fhir/metadata`: `CapabilityStatement` del servicio.
- `GET /fhir/Organization`: consulta de IPS.
- `GET /fhir/Organization/{id}`: consulta de una IPS por identificador interno.
- `GET /fhir/Patient`: consulta de pacientes.
- `GET /fhir/Patient/{id}`: consulta de un paciente por identificador interno.
- `GET /fhir/Practitioner/{id}`: consulta de prestador.
- `GET /fhir/PractitionerRole?specialty={codigo_reps}`: consulta de prestadores por especialidad.
- `GET /fhir/Schedule?actor=Practitioner/{id}`: consulta de agenda por prestador.
- `GET /fhir/Slot?schedule=Schedule/{id}&start=YYYY-MM-DD`: consulta de slots por agenda y fecha.
- `GET /fhir/Slot?schedule=Schedule/{id}&start=YYYY-MM-DD&status=free`: consulta de slots filtrados por estado.
- `GET /fhir/Appointment?patient=Patient/{id}`: consulta de citas por paciente.
- `GET /fhir/Appointment/{id}`: consulta de una cita por identificador.
- `POST /fhir/Appointment`: creación de cita.
- `PATCH /fhir/Appointment/{id}`: cancelación o reagendamiento de cita.
- `PUT /fhir/Appointment/{id}`: actualización de cita.
- `GET /fhir/health`: verificación simple de salud del servicio.

El mock publica `codigo_reps` en los `CodeableConcept` de especialidad para `PractitionerRole`, `Schedule` y `Appointment`. En el estado actual se identifican estas especialidades: Medicina General `101`, Cardiología `302`, Dermatología `312`, Gastroenterología `315`, Ginecobstetricia `318`, Neurología `329`, Oftalmología `330`, Ortopedia `331`, Pediatría `335` y Psicología `342`.

En esta fase, el mock valida contratos HL7 FHIR R4, pero no exige autenticación SMART on FHIR para consumir `Slot` y `Appointment`. La capa SMART puede extenderse posteriormente sin cambiar los recursos FHIR actuales.

## Relación con otros repositorios

Este repositorio funciona como servicio mock de integración para el ecosistema Medix. Su responsabilidad es simular sistemas de agenda de IPS y permitir que otros componentes del proyecto consulten disponibilidad y gestionen citas mediante contratos FHIR.

La relación exacta con otros repositorios debe ser documentada por el equipo de desarrollo.

## Estado del proyecto

Prototipo académico finalizado.

## Convenciones

- Nombres de ramas: se recomienda usar prefijos descriptivos como `feature/`, `fix/`, `docs/` y `chore/`.
- Estilo de commits: se recomienda usar Conventional Commits, por ejemplo `feat:`, `fix:`, `docs:`, `test:` y `chore:`.
- Estructura de carpetas: mantener la separación actual entre rutas, servicios, modelos, base de datos, seguridad y pruebas.
- Uso de variables de entorno: no versionar archivos `.env` con secretos reales; usar `.env.example` como referencia.
- Formato de código: seguir convenciones PEP 8 para Python y mantener nombres claros para recursos FHIR y servicios de dominio.
- Pruebas: agregar o actualizar pruebas en `tests/` cuando se modifiquen contratos FHIR o reglas de citas.
- API: mantener los endpoints FHIR bajo `/fhir` y responder con `application/fhir+json` cuando aplique.

## Autores

Proyecto desarrollado como parte del trabajo de grado.

Equipo de desarrollo:

* Adrián Eduardo Ruiz Cerquera
* Leonardo Velázquez Colin
* Diego Alejandro Jara Rojas
* Jairo Andrés Sierra Combariza

## Licencia

* CC BY-NC 4.0
