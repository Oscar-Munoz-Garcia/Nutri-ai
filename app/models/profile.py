from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.models.daily import ObjetivosMacros

Objetivo = Literal["perder_grasa", "mantenimiento", "ganar_masa"]


class PerfilUsuario(BaseModel):
    nombre: str = Field(default="Oscar", description="Nombre del usuario")
    apellidos: str = Field(default="", description="Apellidos del usuario")
    edad: int = Field(default=24, description="Edad en años")
    peso_kg: float = Field(default=75.0, description="Peso actual en kilogramos")
    altura_cm: float = Field(default=178.0, description="Altura en centímetros")
    genero: Literal["hombre", "mujer"] = Field(default="hombre", description="Género para fórmulas metabólicas")
    nivel_actividad: Literal["sedentario", "ligero", "moderado", "intenso"] = Field(
        default="moderado", 
        description="Nivel de actividad física diaria"
    )
    modo_objetivo: Literal["manual_macros", "manual_calorias", "mifflin_st_jeor"] = Field(
        default="manual_macros",
        description="Método preferido para definir objetivos de nutrición"
    )
    objetivo: Objetivo = Field(default="mantenimiento", description="Meta física: ajusta las calorías calculadas")
    objetivos_diarios: ObjetivosMacros = Field(
        default_factory=lambda: ObjetivosMacros(
            calorias_objetivo=2200.0,
            proteinas_objetivo=160.0,
            carbohidratos_objetivo=210.0,
            grasas_objetivo=70.0
        ),
        description="Límites diarios configurados"
    )
    dias_libres_semana: int = Field(default=1, ge=0, le=7, description="Días libres (comidas fuera) permitidos por semana")


class PerfilActualizar(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    objetivo: Optional[Objetivo] = None
    edad: Optional[int] = None
    peso_kg: Optional[float] = None
    altura_cm: Optional[float] = None
    genero: Optional[Literal["hombre", "mujer"]] = None
    nivel_actividad: Optional[Literal["sedentario", "ligero", "moderado", "intenso"]] = None
    modo_objetivo: Literal["manual_macros", "manual_calorias", "mifflin_st_jeor"] = "manual_macros"
    
    # Para modo manual por macros exactos
    proteinas_g: Optional[float] = None
    carbohidratos_g: Optional[float] = None
    grasas_g: Optional[float] = None
    
    # Para modo manual por calorías totales
    calorias_totales: Optional[float] = None

    dias_libres_semana: Optional[int] = Field(default=None, ge=0, le=7)


class CuestionarioRegistro(BaseModel):
    """Datos que rellena un usuario nuevo al darse de alta con Google."""
    nombre: str = Field(..., min_length=1, max_length=60)
    apellidos: str = Field(..., min_length=1, max_length=100)
    edad: int = Field(..., ge=12, le=100)
    peso_kg: float = Field(..., gt=20, lt=400)
    altura_cm: float = Field(..., gt=100, lt=250)
    genero: Literal["hombre", "mujer"]
    nivel_actividad: Literal["sedentario", "ligero", "moderado", "intenso"]
    objetivo: Objetivo
