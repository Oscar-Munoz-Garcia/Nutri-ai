from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated, List, Optional

NombreComida = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
# Entre 1 y 8 comidas al día, cada una con el nombre que quiera el usuario
ListaComidas = Annotated[List[NombreComida], Field(min_length=1, max_length=8)]


class PlanEntrada(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=40, description="Nombre del plan, p. ej. «Entrenamiento»")
    calorias_objetivo: float = Field(..., gt=0, lt=10000)
    proteinas_objetivo: float = Field(..., ge=0, lt=1000)
    carbohidratos_objetivo: float = Field(..., ge=0, lt=2000)
    grasas_objetivo: float = Field(..., ge=0, lt=1000)
    comidas: Optional[ListaComidas] = Field(default=None, description="Nombres de las comidas del día, en orden; null las deja como estaban")


class Plan(PlanEntrada):
    id: int
    comidas: List[str] = Field(..., description="Nombres de las comidas del día, en orden")
    es_principal: bool = Field(..., description="El plan principal refleja los objetivos del perfil")
    dias_semana: List[int] = Field(default=[], description="Días en los que toca (0 = lunes ... 6 = domingo)")


class PlanesUsuario(BaseModel):
    planes: List[Plan]
    semana: List[int] = Field(..., description="Id del plan de cada día de la semana, de lunes a domingo")


class AsignacionSemana(BaseModel):
    semana: List[int] = Field(..., min_length=7, max_length=7, description="Id del plan de lunes a domingo")


class CambioPlanDia(BaseModel):
    plan_id: Optional[int] = Field(default=None, description="Plan para esa fecha; null vuelve al de la semana")


class PlanDelDia(BaseModel):
    fecha: str
    plan_id: int
    nombre: str
    calorias_objetivo: float
    plan_semanal_id: int = Field(..., description="Plan que toca ese día según la semana")
    cambiado: bool = Field(..., description="True si ese día se cambió a mano")
