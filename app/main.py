from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from typing import List, Optional

from app.core.config import settings
from app.models.user import PerfilUsuario, ObjetivoMacros
from app.models.food import ProductoNutricional
from app.models.pantry import ItemDespensa, RegistroComidaEntrada, RegistroComidaSalida, ResumenDiarioMacros

from app.services.macro_service import calcular_objetivo_macros
from app.services.openfoodfacts_service import consultar_open_food_facts
from app.services import pantry_service

app = FastAPI(title=settings.PROJECT_NAME)


@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    return {
        "estado": "ok",
        "proyecto": settings.PROJECT_NAME,
        "entorno": settings.ENVIRONMENT
    }


# --- OBJETIVO Y MACROS ---
@app.post("/api/v1/macros/calcular", response_model=ObjetivoMacros)
def calcular_macros(perfil: PerfilUsuario):
    return calcular_objetivo_macros(perfil)


# --- ESCÁNER OPEN FOOD FACTS ---
@app.get("/api/v1/alimentos/escaneo/{codigo_barras}", response_model=ProductoNutricional)
async def escanear_producto(codigo_barras: str):
    producto = await consultar_open_food_facts(codigo_barras)
    if not producto:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ningún producto con el código de barras '{codigo_barras}'."
        )
    return producto


# --- DESPENSA VIRTUAL ---
@app.get("/api/v1/despensa", response_model=List[ItemDespensa])
def obtener_despensa():
    """Obtiene la lista de alimentos disponibles en la despensa."""
    return pantry_service.listar_despensa()


@app.post("/api/v1/despensa", response_model=ItemDespensa)
def agregar_alimento_despensa(item: ItemDespensa):
    """Agrega un nuevo alimento a la despensa o suma cantidad si ya existe."""
    return pantry_service.agregar_o_actualizar_despensa(item)


# --- REGISTRO DIARIO DE COMIDAS ---
@app.post("/api/v1/diario/registrar", response_model=RegistroComidaSalida)
def registrar_comida_diario(entrada: RegistroComidaEntrada):
    """Registra una ingesta diaria y opcionalmente resta de la despensa."""
    return pantry_service.registrar_comida(entrada)


@app.get("/api/v1/diario/resumen", response_model=ResumenDiarioMacros)
def resumen_diario(fecha: Optional[str] = None):
    """Muestra el total de calorías y macros consumidos en la fecha indicada (YYYY-MM-DD)."""
    return pantry_service.obtener_resumen_diario(fecha)