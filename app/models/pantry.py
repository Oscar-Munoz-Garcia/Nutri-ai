from pydantic import BaseModel, Field
from typing import Optional, Union
from app.models.daily import RegistroConsumo, ResumenDiario


class AlimentoPantryEntrada(BaseModel):
    nombre: str = Field(..., description="Nombre del alimento")
    cantidad_gramos: float = Field(default=100.0, description="Cantidad disponible en gramos")
    calorias_100g: float = Field(default=0.0, description="Calorías por cada 100g")
    proteinas_100g: float = Field(default=0.0, description="Proteínas en gramos por cada 100g")
    carbohidratos_100g: float = Field(default=0.0, description="Carbohidratos en gramos por cada 100g")
    grasas_100g: float = Field(default=0.0, description="Grasas en gramos por cada 100g")


class AlimentoPantry(AlimentoPantryEntrada):
    id: Optional[Union[str, int]] = Field(default=None, description="ID único del alimento en despensa")


# Alias y re-exportaciones para compatibilidad completa en pantry_service.py y main.py
AlimentoDespensa = AlimentoPantry
AlimentoDespensaEntrada = AlimentoPantryEntrada
ItemDespensa = AlimentoPantry

RegistroComidaEntrada = RegistroConsumo
RegistroComidaSalida = RegistroConsumo
ResumenDiarioMacros = ResumenDiario