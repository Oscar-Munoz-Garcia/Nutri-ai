from pydantic import BaseModel, Field
from typing import List, Optional


class IngredienteReceta(BaseModel):
    nombre: str = Field(..., description="Nombre del ingrediente")
    cantidad_gramos: float = Field(..., gt=0, description="Gramos necesarios por ración")
    calorias_100g: float = Field(default=0.0, ge=0)
    proteinas_100g: float = Field(default=0.0, ge=0)
    carbohidratos_100g: float = Field(default=0.0, ge=0)
    grasas_100g: float = Field(default=0.0, ge=0)


class RecetaEntrada(BaseModel):
    nombre: str = Field(..., description="Nombre comercial de la receta")
    descripcion: Optional[str] = Field(default="", description="Breve descripción o categoría")
    tiempo_preparacion_min: int = Field(..., gt=0, description="Tiempo de preparación en minutos")
    utensilios_necesarios: List[str] = Field(
        ..., description="Lista de utensilios (ej: ['airfryer', 'sarten', 'batidora'])"
    )
    ingredientes: List[IngredienteReceta] = Field(..., description="Lista de ingredientes requeridos")
    pasos: List[str] = Field(..., description="Pasos explicativos para la elaboración")


class RecetaSalida(RecetaEntrada):
    id: str
    calorias_totales: float
    proteinas_totales: float
    carbohidratos_totales: float
    grasas_totales: float