from pydantic import BaseModel, Field
from typing import Optional


class ProductoNutricional(BaseModel):
    codigo_barras: str = Field(..., description="Código EAN-13 o UPC del producto")
    nombre: str = Field(..., description="Nombre comercial del producto")
    marca: Optional[str] = Field(default="Desconocida", description="Marca o fabricante")
    calorias_100g: float = Field(default=0.0, description="Calorías (kcal) por 100g")
    proteinas_100g: float = Field(default=0.0, description="Gramos de proteína por 100g")
    carbohidratos_100g: float = Field(default=0.0, description="Gramos de carbohidratos por 100g")
    grasas_100g: float = Field(default=0.0, description="Gramos de grasa por 100g")
    imagen_url: Optional[str] = Field(default=None, description="URL de la imagen del producto")