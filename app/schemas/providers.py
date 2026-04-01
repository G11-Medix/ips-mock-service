from datetime import datetime

from pydantic import BaseModel


class EspecialidadRead(BaseModel):
    id: int
    nombre: str


class PrestadorRead(BaseModel):
    id: int
    nombre_completo: str
    id_especialidad: int


class CupoRead(BaseModel):
    id_prestador: int
    fecha_hora: datetime
    disponible: bool
    bloqueado: bool
