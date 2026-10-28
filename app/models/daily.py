from pydantic import BaseModel, Field
from typing import List, Optional


class ObjetivosMacros(BaseModel):
    calorias_objetivo: float = Field(default=2200.0, description="Objetivo diario de calorías")
    proteinas_objetivo: float = Field(default=160.0, description="Objetivo diario de proteínas en gramos")
    carbohidratos_objetivo: float = Field(default=210.0, description="Objetivo diario de carbohidratos en gramos")
    grasas_objetivo: float = Field(default=70.0, description="Objetivo diario de grasas en gramos")


class RegistroConsumo(BaseModel):
    id: Optional[int] = Field(default=None, description="ID del registro en el diario (solo en respuestas)")
    nombre: str = Field(..., description="Nombre del alimento o receta consumida")
    calorias: float = Field(..., description="Calorías aportadas")
    proteinas: float = Field(..., description="Proteínas aportadas en gramos")
    carbohidratos: float = Field(..., description="Carbohidratos aportados en gramos")
    grasas: float = Field(..., description="Grasas aportadas en gramos")


class PlanAplicado(BaseModel):
    id: int
    nombre: str
    es_principal: bool


class ResumenDiario(BaseModel):
    fecha: Optional[str] = None
    plan: Optional[PlanAplicado] = Field(default=None, description="Plan de nutrición que se aplica ese día")
    calorias_totales: float
    proteinas_totales: float
    carbohidratos_totales: float
    grasas_totales: float
    objetivos: ObjetivosMacros
    calorias_restantes: float
    proteinas_restantes: float
    carbohidratos_restantes: float
    grasas_restantes: float
    registros: List[RegistroConsumo]