from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse
from typing import List, Optional

from app.core.config import settings
from app.models.user import PerfilUsuario, ObjetivoMacros
from app.models.food import ProductoNutricional
from app.models.pantry import ItemDespensa, RegistroComidaEntrada, RegistroComidaSalida, ResumenDiarioMacros

from app.services.macro_service import calcular_objetivo_macros
from app.services.openfoodfacts_service import consultar_open_food_facts
from app.services import pantry_service
from app.services.vision_service import analizar_etiqueta_imagen

from app.models.recommendation import SolicitudRecomendacion, RecomendacionResultado
from app.services import recommendation_service

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


# --- OCR Y VISIÓN CON LLM ---
@app.post("/api/v1/alimentos/vision-ocr", response_model=ProductoNutricional)
async def procesar_etiqueta_vision(file: UploadFile = File(...)):
    """
    Sube una foto de una tabla/etiqueta nutricional para extraer
    automáticamente los datos mediante Visión por Inteligencia Artificial.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo subido debe ser una imagen válida (JPG, PNG, WEBP)."
        )

    contenido_bytes = await file.read()
    producto = await analizar_etiqueta_imagen(contenido_bytes, file.content_type)
    return producto


# --- DESPENSA VIRTUAL ---
@app.get("/api/v1/despensa", response_model=List[ItemDespensa])
def obtener_despensa():
    return pantry_service.listar_despensa()


@app.post("/api/v1/despensa", response_model=ItemDespensa)
def agregar_alimento_despensa(item: ItemDespensa):
    return pantry_service.agregar_o_actualizar_despensa(item)


# --- REGISTRO DIARIO DE COMIDAS ---
@app.post("/api/v1/diario/registrar", response_model=RegistroComidaSalida)
def registrar_comida_diario(entrada: RegistroComidaEntrada):
    return pantry_service.registrar_comida(entrada)


@app.get("/api/v1/diario/resumen", response_model=ResumenDiarioMacros)
def resumen_diario(fecha: Optional[str] = None):
    return pantry_service.obtener_resumen_diario(fecha)

# --- RECOMENDADOR NUTRICIONAL INTELIGENTE ---
@app.post("/api/v1/recomendaciones/sugerir", response_model=List[RecomendacionResultado])
def sugerir_recetas(solicitud: SolicitudRecomendacion):
    """
    Calcula los macros pendientes del día y cruza la despensa y los utensilios
    disponibles para recomendar las mejores recetas que completan la meta diaria.
    """
    return recommendation_service.obtener_sugerencias_recetas(solicitud)