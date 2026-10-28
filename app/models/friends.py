from pydantic import BaseModel, Field
from typing import List


class SolicitudAmistadEntrada(BaseModel):
    usuario: str = Field(..., min_length=1, description="Nombre de usuario o email de la persona a agregar")


class UsuarioPublico(BaseModel):
    usuario_id: int
    username: str


class SolicitudAmistad(BaseModel):
    id: int
    usuario: UsuarioPublico = Field(..., description="La otra persona de la solicitud")
    fecha: str


class Amigos(BaseModel):
    amigos: List[UsuarioPublico]
    recibidas: List[SolicitudAmistad]
    enviadas: List[SolicitudAmistad]
