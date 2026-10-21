from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.models.daily import ObjetivosMacros


class PerfilUsuario(BaseModel):
    nombre: str = Field(default="Oscar", description="Nombre del usuario")
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
    objetivos_diarios: ObjetivosMacros = Field(
        default_factory=lambda: ObjetivosMacros(
            calorias_objetivo=2200.0,
            proteinas_objetivo=160.0,
            carbohidratos_objetivo=210.0,
            grasas_objetivo=70.0
        ),
        description="Límites diarios configurados"
    )


class PerfilActualizar(BaseModel):
    nombre: Optional[str] = None
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