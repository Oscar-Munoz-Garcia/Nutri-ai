from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date


class ItemDespensa(BaseModel):
    id: Optional[str] = Field(default=None, description="Identificador único del alimento en despensa")
    nombre: str = Field(..., description="Nombre del alimento o ingrediente")
    cantidad_gramos: float = Field(..., gt=0, description="Cantidad disponible en gramos o ml")
    calorias_100g: float = Field(default=0.0, ge=0)
    proteinas_100g: float = Field(default=0.0, ge=0)
    carbohidratos_100g: float = Field(default=0.0, ge=0)
    grasas_100g: float = Field(default=0.0, ge=0)
    categoria: Optional[str] = Field(default="general", description="Categoría (ej: proteina, verdura, lacteo)")


class RegistroComidaEntrada(BaseModel):
    nombre_alimento: str = Field(..., description="Nombre del alimento consumido")
    cantidad_gramos: float = Field(..., gt=0, description="Gramos o ml consumidos")
    momento_dia: Literal["desayuno", "comida", "cena", "snack"] = Field(..., description="Momento de la ingesta")
    calorias_100g: float = Field(default=0.0, ge=0)
    proteinas_100g: float = Field(default=0.0, ge=0)
    carbohidratos_100g: float = Field(default=0.0, ge=0)
    grasas_100g: float = Field(default=0.0, ge=0)
    descontar_de_despensa: bool = Field(default=True, description="Si es True, resta la cantidad de la despensa si existe")


class RegistroComidaSalida(BaseModel):
    id: str
    fecha: str
    nombre_alimento: str
    cantidad_gramos: float
    momento_dia: str
    calorias_totales: float
    proteinas_totales: float
    carbohidratos_totales: float
    grasas_totales: float


class ResumenDiarioMacros(BaseModel):
    fecha: str
    calorias_totales: float
    proteinas_totales: float
    carbohidratos_totales: float
    grasas_totales: float
    comidas_registradas: list[RegistroComidaSalida]