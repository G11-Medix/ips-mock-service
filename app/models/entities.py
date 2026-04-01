from datetime import date, datetime

from sqlmodel import Field, SQLModel


class IPS(SQLModel, table=True):
    id_ips: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    codigo: str | None = Field(default=None, index=True, unique=True)
    nit: str = Field(index=True, unique=True)
    direccion: str | None = None
    telefono: str | None = None
    estado: str = Field(default="activo", index=True)


class Paciente(SQLModel, table=True):
    id_paciente: int | None = Field(default=None, primary_key=True)
    tipo_documento: str = Field(index=True)
    numero_documento: str = Field(index=True)
    nombres: str = Field(index=True)
    apellidos: str = Field(index=True)
    fecha_nacimiento: date
    telefono: str | None = None
    correo: str | None = None
    estado: str = Field(default="activo", index=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Specialty(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)


class Provider(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(index=True)
    specialty_id: int = Field(foreign_key="specialty.id", index=True)


class Appointment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="paciente.id_paciente", index=True)
    provider_id: int = Field(foreign_key="provider.id", index=True)
    specialty_id: int = Field(foreign_key="specialty.id", index=True)
    slot_start: datetime = Field(index=True)
    status: str = Field(default="scheduled", index=True)
    cancel_reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
