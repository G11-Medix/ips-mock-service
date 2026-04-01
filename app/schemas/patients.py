from datetime import date, datetime

from pydantic import BaseModel


class PacienteRead(BaseModel):
    id_paciente: int
    tipo_documento: str
    numero_documento: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    telefono: str | None
    correo: str | None
    estado: str
    fecha_creacion: datetime


class PacienteSummary(BaseModel):
    id_paciente: int
    tipo_documento: str
    numero_documento: str
    nombres: str
    apellidos: str
