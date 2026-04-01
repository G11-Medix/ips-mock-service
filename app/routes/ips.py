from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.db.session import get_session
from app.models.entities import IPS
from app.schemas.ips import IPSActualRead

router = APIRouter(prefix="/api/v1/ips", tags=["ips"])
settings = get_settings()


@router.get("/actual", response_model=IPSActualRead)
def get_ips_actual(session: Session = Depends(get_session)) -> IPS:
    ips = session.exec(select(IPS).where(IPS.codigo == settings.ips_code)).first()
    if ips is None:
        ips = session.exec(select(IPS).where(IPS.nit == settings.ips_nit)).first()
    if ips is None:
        raise HTTPException(status_code=404, detail="IPS de la instancia no encontrada")
    return ips
