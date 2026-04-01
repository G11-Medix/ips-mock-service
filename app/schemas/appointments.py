from datetime import datetime

from pydantic import BaseModel, Field


class CitaCrear(BaseModel):
    id_paciente: int
    id_prestador: int
    fecha_hora_cupo: datetime


class CitaRead(BaseModel):
    id: int
    id_paciente: int
    id_prestador: int
    id_especialidad: int
    fecha_hora_cupo: datetime
    estado: str
    motivo_cancelacion: str | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class CitaCancelar(BaseModel):
    motivo: str | None = Field(default=None, max_length=200)


class CitaReprogramar(BaseModel):
    nueva_fecha_hora_cupo: datetime
