from pydantic import BaseModel, Field
from typing import List, Optional


class PesoEntrada(BaseModel):
    peso_kg: float = Field(..., gt=20, lt=400, description="Peso corporal en kilogramos")
    fecha: Optional[str] = Field(default=None, description="Fecha ISO (YYYY-MM-DD). Por defecto, hoy")


class PesoRegistro(BaseModel):
    id: int
    fecha: str
    peso_kg: float


class TDEEDinamico(BaseModel):
    estado: str = Field(..., description="'ok' si hay datos suficientes, 'insuficiente' si no")
    mensaje: str
    tdee_real: Optional[float] = Field(default=None, description="Gasto calórico diario estimado (kcal)")
    tdee_teorico: float = Field(..., description="TDEE por fórmula Mifflin-St Jeor como referencia")
    ingesta_media: Optional[float] = None
    tendencia_kg_semana: Optional[float] = Field(default=None, description="Pendiente de la regresión en kg/semana")
    r2: Optional[float] = Field(default=None, description="Bondad del ajuste de la regresión (0-1)")
    dias_ventana: int
    dias_con_registro: int
    num_pesajes: int
    pesajes: List[PesoRegistro] = []
    recta: List[float] = Field(default=[], description="Peso ajustado por la regresión en cada pesaje")


class DiaCumplimiento(BaseModel):
    fecha: str
    calorias: Optional[float] = Field(default=None, description="Solo visible para el propio usuario")
    proteinas: Optional[float] = Field(default=None, description="Solo visible para el propio usuario")
    puntuacion: float


class CumplimientoUsuario(BaseModel):
    usuario_id: int
    nombre: str
    es_yo: bool
    porcentaje_semana: float
    porcentaje_semana_anterior: float
    dias_cumplidos: int
    dias_evaluados: int
    dias: List[DiaCumplimiento]


class Versus(BaseModel):
    semana_inicio: str
    semana_fin: str
    lider_id: Optional[int] = None
    participantes: List[CumplimientoUsuario]
