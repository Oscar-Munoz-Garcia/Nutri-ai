from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.models.user import PerfilUsuario, ObjetivoMacros
from app.models.food import ProductoNutricional
from app.services.macro_service import calcular_objetivo_macros
from app.services.openfoodfacts_service import consultar_open_food_facts

app = FastAPI(title=settings.PROJECT_NAME)


@app.get("/", include_in_schema=False)
def inicio():
    """Redirige la raíz a la documentación Swagger."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    return {
        "estado": "ok",
        "proyecto": settings.PROJECT_NAME,
        "entorno": settings.ENVIRONMENT
    }


@app.post("/api/v1/macros/calcular", response_model=ObjetivoMacros)
def calcular_macros(perfil: PerfilUsuario):
    """
    Calcula el BMR, TDEE, calorías diarias y reparto de macronutrientes objetivo
    a partir del perfil antropométrico del usuario.
    """
    return calcular_objetivo_macros(perfil)


@app.get("/api/v1/alimentos/escaneo/{codigo_barras}", response_model=ProductoNutricional)
async def escanear_producto(codigo_barras: str):
    """
    Busca la información nutricional por 100g de un producto
    a partir de su código de barras usando Open Food Facts.
    """
    producto = await consultar_open_food_facts(codigo_barras)
    if not producto:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ningún producto con el código de barras '{codigo_barras}'."
        )
    return producto
