from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.entities import EPS, Institucion, InstitucionEPS, Paciente
from app.schemas.afiliaciones import AfiliacionValidacionRead, InstitucionAfiliacionRead

router = APIRouter(prefix="/api/v1/afiliaciones", tags=["afiliaciones"])


@router.get("/validar", response_model=AfiliacionValidacionRead)
def validar_afiliacion(
    tipo_documento: str = Query(...),
    numero_documento: str = Query(...),
    codigo_eps: str = Query(...),
    session: Session = Depends(get_session),
) -> AfiliacionValidacionRead:
    paciente = session.exec(
        select(Paciente).where(
            Paciente.tipo_documento == tipo_documento,
            Paciente.numero_documento == numero_documento,
        )
    ).first()

    if paciente is None:
        return AfiliacionValidacionRead(
            afiliado=False,
            codigo_eps=codigo_eps,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            id_paciente=None,
            institucion=None,
            detalle="Paciente no encontrado",
        )

    match = session.exec(
        select(Institucion)
        .join(InstitucionEPS, Institucion.id_institucion == InstitucionEPS.id_institucion)
        .join(EPS, EPS.id_eps == InstitucionEPS.id_eps)
        .where(
            Institucion.id_institucion == paciente.id_institucion,
            EPS.codigo == codigo_eps,
        )
    ).first()

    if match is None:
        return AfiliacionValidacionRead(
            afiliado=False,
            codigo_eps=codigo_eps,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            id_paciente=paciente.id_paciente,
            institucion=None,
            detalle="Paciente no afiliado a la EPS consultada",
        )

    return AfiliacionValidacionRead(
        afiliado=True,
        codigo_eps=codigo_eps,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        id_paciente=paciente.id_paciente,
        institucion=InstitucionAfiliacionRead(
            id_institucion=match.id_institucion,
            nombre=match.nombre,
            nit=match.nit,
        ),
        detalle="Paciente afiliado a la EPS consultada",
    )
