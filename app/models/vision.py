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
