# Mock EPS/IPS para integraciones

Servicio mock parametrizable por instancia EPS para exponer datos maestros (EPS, IPS, pacientes) y validar afiliaciones, manteniendo el flujo de citas.

## Stack
- Python 3.11
- FastAPI
- SQLModel + SQLite
- Docker + Docker Compose

## Variables de entorno
Ver `.env.example`.

- `EPS_NAME`
- `EPS_SLUG`
- `EPS_CODE`
- `TIMEZONE`
- `PORT`
- `API_KEY`
- `DB_PATH`

## Ejecutar local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 4011
```

Swagger:
- `http://localhost:4011/docs`

## Ejecutar con Docker Compose (3 EPS)
```bash
docker compose up --build
```

Instancias:
- `eps_sanitas`: `http://localhost:4011`
- `eps_nuevaeps`: `http://localhost:4012`
- `eps_saludtotal`: `http://localhost:4013`

Cada instancia usa su propia base SQLite en:
- `./data/sanitas/eps.db`
- `./data/nuevaeps/eps.db`
- `./data/saludtotal/eps.db`

## Endpoints
Base API: `/api/v1`

### Datos maestros
- `GET /api/v1/eps`
- `GET /api/v1/ips`
- `GET /api/v1/ips?nit={nit}`
- `GET /api/v1/ips?codigo_eps={codigo}`
- `GET /api/v1/ips/{nit}`
- `GET /api/v1/pacientes`
- `GET /api/v1/pacientes?tipo_documento=&numero_documento=&codigo_eps=`
- `GET /api/v1/pacientes/{tipo_documento}/{numero_documento}`

### Validacion de afiliacion
- `GET /api/v1/afiliaciones/validar?tipo_documento=&numero_documento=&codigo_eps=`

### Citas (se mantiene)
- `GET /api/v1/specialties`
- `GET /api/v1/providers`
- `GET /api/v1/providers/{id}/slots?date=YYYY-MM-DD`
- `POST /api/v1/appointments`
- `GET /api/v1/appointments/{id}`
- `GET /api/v1/appointments?patient_id=&from=&to=`
- `PATCH /api/v1/appointments/{id}/cancel`
- `PATCH /api/v1/appointments/{id}/reschedule`

## Seeder inicial
El seeder crea datos deterministas por instancia:
- EPS base (incluyendo la EPS principal de la instancia por `EPS_CODE`)
- IPS con NIT fijo
- Vinculos IPS-EPS (`InstitucionEPS`)
- Pacientes afiliados y no afiliados
- Especialidades y providers para agenda

## Ejemplos curl
Listado EPS:
```bash
curl -s http://localhost:4011/api/v1/eps -H 'x-api-key: sanitas-key'
```

Listado IPS afiliadas a una EPS:
```bash
curl -s 'http://localhost:4011/api/v1/ips?codigo_eps=EPS-SAN' -H 'x-api-key: sanitas-key'
```

Consultar paciente por documento:
```bash
curl -s 'http://localhost:4011/api/v1/pacientes/CC/1002003001' -H 'x-api-key: sanitas-key'
```

Validar afiliacion:
```bash
curl -s 'http://localhost:4011/api/v1/afiliaciones/validar?tipo_documento=CC&numero_documento=1002003001&codigo_eps=EPS-SAN' \
  -H 'x-api-key: sanitas-key'
```
