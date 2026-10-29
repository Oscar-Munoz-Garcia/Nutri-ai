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

class AlimentoPor100g(BaseModel):
    """Alimento del buscador del diario: valores por 100 g para calcular los macros de los gramos que se coman."""
    nombre: str
    nombre_en: Optional[str] = Field(default=None, description="Nombre en inglés (solo alimentos de la base)")
    origen: str = Field(..., description="'despensa' (tus alimentos), 'receta' (tus recetas) o 'base' (alimentos comunes)")
    receta_id: Optional[str] = Field(default=None, description="Solo recetas")
    por_racion: bool = Field(default=False, description="True en recetas: los valores *_100g son de una ración (la receta entera)")
    gramos_racion: Optional[float] = Field(default=None, description="Peso de una ración, si la receta tiene los gramos de sus ingredientes")
    calorias_100g: float
    proteinas_100g: float
    carbohidratos_100g: float
    grasas_100g: float
