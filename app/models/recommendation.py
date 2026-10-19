from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.recipe import RecetaSalida


class SolicitudRecomendacion(BaseModel):
    calorias_objetivo: float = Field(..., gt=0, description="Calorías objetivo del día")
    proteinas_objetivo: float = Field(..., gt=0, description="Proteínas objetivo en gramos")
    carbohidratos_objetivo: float = Field(..., gt=0, description="Carbohidratos objetivo en gramos")
    grasas_objetivo: float = Field(..., gt=0, description="Grasas objetivo en gramos")
    utensilios_disponibles: Optional[List[str]] = Field(
        default=None, description="Utensilios de cocina disponibles (ej: ['airfryer', 'batidora'])"
    )


class RecomendacionResultado(BaseModel):
    receta: RecetaSalida
    coincidencia_porcentaje: float = Field(..., description="Porcentaje de ajuste al hueco calórico y proteico")
    ingredientes_faltantes: List[str] = Field(default=[], description="Ingredientes requeridos que no hay en despensa")
    puntuacion_explicacion: str = Field(..., description="Explicación del ajuste nutricional")