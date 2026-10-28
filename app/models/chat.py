from pydantic import BaseModel, Field
from typing import List, Optional


class MensajeChat(BaseModel):
    role: str = Field(..., description="'user', 'assistant' o 'system'")
    content: str = Field(..., description="Contenido textual del mensaje")


class SolicitudChat(BaseModel):
    historial: List[MensajeChat] = Field(..., description="Historial de mensajes de la conversación")
    calorias_pendientes: Optional[float] = Field(default=None, description="Calorías faltantes en el día")
    proteinas_pendientes: Optional[float] = Field(default=None, description="Proteínas faltantes en gramos")
    idioma: str = Field(default="es", description="Idioma de la interfaz ('es' o 'en'); el agente responde en él")


class RespuestaChat(BaseModel):
    respuesta: str = Field(..., description="Respuesta generada por el agente")
    herramientas_usadas: List[str] = Field(default=[], description="Lista de herramientas ejecutadas de forma determinista")