from pydantic import BaseModel, Field
from typing import List, Optional, Union


class IngredienteReceta(BaseModel):
    nombre: str = Field(..., description="Nombre del ingrediente")
    cantidad_gramos: float = Field(..., description="Cantidad en gramos del ingrediente")


class RecetaCrear(BaseModel):
    nombre: str = Field(..., description="Nombre de la receta")
    descripcion: Optional[str] = Field(default="", description="Descripción o instrucciones breves")
    calorias_totales: float = Field(..., description="Calorías totales de la porción")
    proteinas_totales: float = Field(..., description="Proteínas totales en gramos")
    carbohidratos_totales: float = Field(..., description="Carbohidratos totales en gramos")
    grasas_totales: float = Field(..., description="Grasas totales en gramos")
    tiempo_preparacion_min: int = Field(default=15, description="Tiempo de preparación en minutos")
    utensilios_necesarios: List[str] = Field(default=["Sartén"], description="Lista de utensilios o electrodomésticos necesarios")
    ingredientes: Optional[List[IngredienteReceta]] = Field(default=[], description="Lista opcional de ingredientes")


class Receta(RecetaCrear):
    id: Union[str, int] = Field(..., description="ID único de la receta (acepta texto o número)")


# Alias para garantizar compatibilidad con imports en main.py y recipe_service.py
RecetaEntrada = RecetaCrear
RecetaSalida = Receta