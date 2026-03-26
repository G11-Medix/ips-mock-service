from pydantic import BaseModel


class InstitucionRead(BaseModel):
    id_institucion: int
    nombre: str
    nit: str
    direccion: str | None
    telefono: str | None
    estado: str
