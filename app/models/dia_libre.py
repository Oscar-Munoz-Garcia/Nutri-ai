from pydantic import BaseModel, Field
from typing import List


class CambioDiaLibre(BaseModel):
    libre: bool = Field(..., description="True marca la fecha como día libre; False la vuelve a contar")


class DiasLibresSemana(BaseModel):
    semana_inicio: str
    semana_fin: str
    limite: int = Field(..., description="Días libres permitidos por semana (perfil)")
    usados: int
    fechas: List[str] = Field(default=[], description="Días libres marcados en esa semana")
