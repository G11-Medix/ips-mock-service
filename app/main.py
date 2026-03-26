from fastapi import FastAPI
from sqlmodel import Session

from app.config import get_settings
from app.core.auth import ApiKeyMiddleware
from app.db.session import create_db_and_tables, engine
from app.routes.afiliaciones import router as afiliaciones_router
from app.routes.appointments import router as appointments_router
from app.routes.eps import router as eps_router
from app.routes.ips import router as ips_router
from app.routes.patients import router as patients_router
from app.routes.providers import router as providers_router
from app.services.seeder import seed_initial_data

settings = get_settings()

app = FastAPI(title=f"{settings.eps_name} - Appointment Mock API", version=settings.version)
app.add_middleware(ApiKeyMiddleware)

app.include_router(eps_router)
app.include_router(ips_router)
app.include_router(patients_router)
app.include_router(afiliaciones_router)
app.include_router(providers_router)
app.include_router(appointments_router)


@app.on_event("startup")
def startup_event() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        seed_initial_data(session)
