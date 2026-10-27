from pydantic import BaseModel, Field
from typing import Optional, List


class ProductoOCR(BaseModel):
    nombre: str = Field(default="Producto Detectado", description="Nombre del producto o alimento identificado")
    calorias_100g: float = Field(default=0.0, description="Calorías por cada 100g")
    proteinas_100g: float = Field(default=0.0, description="Proteínas por cada 100g")
    carbohidratos_100g: float = Field(default=0.0, description="Carbohidratos por cada 100g")
    grasas_100g: float = Field(default=0.0, description="Grasas por cada 100g")
    ingredientes_detectados: Optional[List[str]] = Field(default=[], description="Lista opcional de ingredientes leídos")
    confianza: Optional[float] = Field(default=1.0, description="Puntaje de confianza del modelo de visión OCR")


class IngredientePlato(BaseModel):
    nombre: str = Field(..., description="Ingrediente identificado en el plato")
    peso_estimado_g: float = Field(default=0.0, description="Peso estimado en gramos")
    calorias: float = Field(default=0.0, description="Calorías aportadas por la porción estimada")
    proteinas: float = Field(default=0.0, description="Proteínas (g) de la porción estimada")
    carbohidratos: float = Field(default=0.0, description="Carbohidratos (g) de la porción estimada")
    grasas: float = Field(default=0.0, description="Grasas (g) de la porción estimada")


class AnalisisPlato(BaseModel):
    nombre_plato: str = Field(default="Plato detectado", description="Nombre descriptivo del plato")
    ingredientes: List[IngredientePlato] = Field(default=[], description="Ingredientes con peso y macros estimados")
    peso_total_g: float = Field(default=0.0, description="Peso total estimado del plato")
    calorias_totales: float = Field(default=0.0)
    proteinas_totales: float = Field(default=0.0)
    carbohidratos_totales: float = Field(default=0.0)
    grasas_totales: float = Field(default=0.0)
    confianza: float = Field(default=0.5, description="Confianza de la estimación entre 0 y 1")
    notas: str = Field(default="", description="Advertencias o supuestos de la estimación")
    modo_prueba: bool = Field(default=False, description="True si se devolvió una estimación simulada sin Groq")
