from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.config import get_settings
from app.db.session import create_db_and_tables, engine
from app.routes.fhir import router as fhir_router
from app.routes.smart import router as smart_router
from app.services.fhir import FHIR_JSON_MEDIA_TYPE, operation_outcome
from app.services.seeder import seed_initial_data

settings = get_settings()

app = FastAPI(title=f"{settings.ips_name} - IPS Appointment Mock API", version=settings.version)

app.include_router(smart_router)
app.include_router(fhir_router)


@app.on_event("startup")
def startup_event() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        seed_initial_data(session)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if not request.url.path.startswith("/fhir"):
        return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code)

    if isinstance(exc.detail, dict) and exc.detail.get("resourceType") == "OperationOutcome":
        return JSONResponse(
            content=exc.detail,
            status_code=exc.status_code,
            media_type=FHIR_JSON_MEDIA_TYPE,
        )

    return JSONResponse(
        content=operation_outcome("exception", str(exc.detail)),
        status_code=exc.status_code,
        media_type=FHIR_JSON_MEDIA_TYPE,
    )
