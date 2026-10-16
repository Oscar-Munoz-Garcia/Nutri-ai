from pydantic import BaseModel, Field
from typing import Literal


class PerfilUsuario(BaseModel):
    edad: int = Field(..., ge=14, le=100, description="Edad en años")
    peso_kg: float = Field(..., gt=30, lt=250, description="Peso corporal en kg")
    altura_cm: float = Field(..., gt=100, lt=250, description="Altura en cm")
    genero: Literal["hombre", "mujer"] = Field(..., description="Género biológico")
    nivel_actividad: Literal["sedentario", "ligero", "moderado", "alto", "extremo"] = Field(
        ..., description="Nivel de actividad física diaria"
    )
    objetivo: Literal["perder_grasa", "mantenimiento", "ganar_masa"] = Field(
        ..., description="Objetivo nutricional"
    )


class ObjetivoMacros(BaseModel):
    bmr_calorias: int = Field(..., description="Tasa Metabólica Basal")
    tdee_calorias: int = Field(..., description="Gasto Energético Total Diario")
    calorias_objetivo: int = Field(..., description="Calorías meta del día")
    proteinas_g: int = Field(..., description="Gramos de proteína diarios")
    carbohidratos_g: int = Field(..., description="Gramos de carbohidratos diarios")
    grasas_g: int = Field(..., description="Gramos de grasa diarios")