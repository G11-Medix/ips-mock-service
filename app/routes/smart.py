from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.security.smart_auth import build_smart_configuration

router = APIRouter(tags=["SMART on FHIR"])


@router.get("/.well-known/smart-configuration")
def smart_configuration() -> JSONResponse:
    settings = get_settings()
    return JSONResponse(content=build_smart_configuration(settings))
