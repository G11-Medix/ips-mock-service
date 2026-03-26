from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.entities import EPS, InstitucionEPS, Paciente
from app.schemas.patients import PacienteRead

router = APIRouter(prefix="/api/v1/pacientes", tags=["pacientes"])


@router.get("", response_model=list[PacienteRead])
def list_pacientes(
    tipo_documento: str | None = Query(default=None),
    numero_documento: str | None = Query(default=None),
    codigo_eps: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[Paciente]:
    if codigo_eps:
        query = (
            select(Paciente)
            .join(InstitucionEPS, Paciente.id_institucion == InstitucionEPS.id_institucion)
            .join(EPS, EPS.id_eps == InstitucionEPS.id_eps)
            .where(EPS.codigo == codigo_eps)
        )
    else:
        query = select(Paciente)

    if tipo_documento:
        query = query.where(Paciente.tipo_documento == tipo_documento)
    if numero_documento:
        query = query.where(Paciente.numero_documento == numero_documento)

    return session.exec(query.order_by(Paciente.id_paciente)).all()


@router.get("/{tipo_documento}/{numero_documento}", response_model=PacienteRead)
def get_paciente(
    tipo_documento: str,
    numero_documento: str,
    codigo_eps: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> Paciente:
    if codigo_eps:
        query = (
            select(Paciente)
            .join(InstitucionEPS, Paciente.id_institucion == InstitucionEPS.id_institucion)
            .join(EPS, EPS.id_eps == InstitucionEPS.id_eps)
            .where(
                Paciente.tipo_documento == tipo_documento,
                Paciente.numero_documento == numero_documento,
                EPS.codigo == codigo_eps,
            )
        )
    else:
        query = select(Paciente).where(
            Paciente.tipo_documento == tipo_documento,
            Paciente.numero_documento == numero_documento,
        )

    paciente = session.exec(query).first()
    if paciente is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return paciente
