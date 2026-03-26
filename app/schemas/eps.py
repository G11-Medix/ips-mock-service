from pydantic import BaseModel


class EPSRead(BaseModel):
    id_eps: int
    nombre: str
    codigo: str
    estado: str
