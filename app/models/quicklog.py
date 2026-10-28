from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.daily import RegistroConsumo


class SolicitudRegistroRapido(BaseModel):
    texto: str = Field(..., min_length=1, max_length=500, description="Frase dictada o escrita, ej: 'Desayuno: 3 huevos cocidos y 80g de avena'")


class ItemInterpretado(RegistroConsumo):
    origen: str = Field(default="ia", description="'despensa' si se calculó con tu despensa, 'ia' si lo estimó Groq, 'sin_estimar' si no hubo forma de calcularlo")


class RespuestaRegistroRapido(BaseModel):
    comida: Optional[str] = Field(default=None, description="Momento del día detectado (Desayuno, Comida, Cena...)")
    items: List[ItemInterpretado] = Field(default_factory=list)
    avisos: List[str] = Field(default_factory=list)
