# Mock IPS para integraciones de agenda

Servicio mock parametrizable por instancia IPS para simular integraciones con sistemas de agendamiento de citas medicas.

## Stack
- Python 3.11
- FastAPI
- SQLModel + SQLite
- Docker + Docker Compose

## Variables de entorno
Ver `.env.example`.

- `IPS_NAME`
- `IPS_SLUG`
- `IPS_CODE`
- `IPS_NIT`
- `TIMEZONE`
- `PORT`
- `API_KEY`
- `DB_PATH`
- `RESET_DB_ON_STARTUP`

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

## Ejecutar con Docker Compose (3 IPS)
```bash
docker compose up --build
```

Instancias:
- `ips_clinica_santa_helena`: `http://localhost:4011`
- `ips_hospital_nuevo_horizonte`: `http://localhost:4012`
- `ips_clinica_prado_caribe`: `http://localhost:4013`

Cada instancia usa su propia base SQLite en:
- `./data/ips-csh/ips.db`
- `./data/ips-hnh/ips.db`
- `./data/ips-cpc/ips.db`


## Seeder inicial
El seeder crea datos deterministas por instancia:
- IPS principal de la instancia (`IPS_NAME`, `IPS_CODE`, `IPS_NIT`)
- Pacientes propios por IPS
- Especialidades y prestadores por IPS
- Una cita demo inicial para pruebas del flujo


## Nota de datos
Por defecto el servicio reinicia y reseed la base al iniciar (`RESET_DB_ON_STARTUP=true`), ideal para pruebas repetibles.
