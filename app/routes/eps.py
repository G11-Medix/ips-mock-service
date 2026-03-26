from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.entities import EPS
from app.schemas.eps import EPSRead

router = APIRouter(prefix="/api/v1/eps", tags=["eps"])


@router.get("", response_model=list[EPSRead])
def list_eps(session: Session = Depends(get_session)) -> list[EPS]:
    return session.exec(select(EPS).order_by(EPS.codigo)).all()
