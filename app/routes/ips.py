from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.entities import EPS, Institucion, InstitucionEPS
from app.schemas.ips import InstitucionRead

router = APIRouter(prefix="/api/v1/ips", tags=["ips"])


@router.get("", response_model=list[InstitucionRead])
def list_ips(
    nit: str | None = Query(default=None),
    codigo_eps: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[Institucion]:
    if codigo_eps:
        query = (
            select(Institucion)
            .join(InstitucionEPS, Institucion.id_institucion == InstitucionEPS.id_institucion)
            .join(EPS, EPS.id_eps == InstitucionEPS.id_eps)
            .where(EPS.codigo == codigo_eps)
        )
    else:
        query = select(Institucion)

    if nit:
        query = query.where(Institucion.nit == nit)

    return session.exec(query.order_by(Institucion.nombre)).all()


@router.get("/{nit}", response_model=InstitucionRead)
def get_ips_by_nit(nit: str, session: Session = Depends(get_session)) -> Institucion:
    ips = session.exec(select(Institucion).where(Institucion.nit == nit)).first()
    if ips is None:
        raise HTTPException(status_code=404, detail="IPS no encontrada")
    return ips
