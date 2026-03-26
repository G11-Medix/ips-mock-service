from pydantic import BaseModel


class InstitucionAfiliacionRead(BaseModel):
    id_institucion: int
    nombre: str
    nit: str


class AfiliacionValidacionRead(BaseModel):
    afiliado: bool
    codigo_eps: str
    tipo_documento: str
    numero_documento: str
    id_paciente: int | None
    institucion: InstitucionAfiliacionRead | None
    detalle: str
