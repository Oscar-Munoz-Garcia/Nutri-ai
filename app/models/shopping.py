from pydantic import BaseModel, Field
from typing import List, Union


class RecetaPlanificada(BaseModel):
    receta_id: Union[str, int] = Field(..., description="ID de la receta que se quiere cocinar")
    raciones: float = Field(default=1.0, gt=0, description="Veces que se cocinará la receta")


class SolicitudListaCompra(BaseModel):
    recetas: List[RecetaPlanificada] = Field(..., min_length=1, description="Recetas planificadas para la semana")


class ItemListaCompra(BaseModel):
    nombre: str
    necesario_g: float = Field(..., description="Gramos totales que piden las recetas")
    disponible_g: float = Field(..., description="Gramos que ya hay en la despensa")
    comprar_g: float = Field(..., description="Gramos que faltan por comprar")
    recetas: List[str] = Field(default=[], description="Recetas que usan este ingrediente")


class ListaCompra(BaseModel):
    faltantes: List[ItemListaCompra] = Field(default=[], description="Ingredientes que hay que comprar")
    cubiertos: List[ItemListaCompra] = Field(default=[], description="Ingredientes que ya están en la despensa")
    recetas_sin_ingredientes: List[str] = Field(default=[], description="Recetas planificadas sin lista de ingredientes")
    recetas_no_encontradas: List[str] = Field(default=[], description="IDs de recetas que no existen")
