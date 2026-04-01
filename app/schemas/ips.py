from pydantic import BaseModel


class IPSActualRead(BaseModel):
    id_ips: int
    nombre: str
    codigo: str | None
    nit: str
    direccion: str | None
    telefono: str | None
    estado: str
