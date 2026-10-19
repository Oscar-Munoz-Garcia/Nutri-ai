from fastapi import FastAPI, HTTPException, File, UploadFile, Query
from fastapi.responses import RedirectResponse
from typing import List, Optional

from app.core.config import settings
from app.models.user import PerfilUsuario, ObjetivoMacros
from app.models.food import ProductoNutricional
from app.models.pantry import ItemDespensa, RegistroComidaEntrada, RegistroComidaSalida, ResumenDiarioMacros
from app.models.recipe import RecetaEntrada, RecetaSalida

from app.services.macro_service import calcular_objetivo_macros
from app.services.openfoodfacts_service import consultar_open_food_facts
from app.services import pantry_service
from app.services.vision_service import analizar_etiqueta_imagen
from app.services import recipe_service

from app.models.chat import SolicitudChat, RespuestaChat
from app.services import agent_service

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


# --- LIBRO DE RECETAS Y UTENSILIOS ---
@app.get("/api/v1/recetas", response_model=List[RecetaSalida])
def listar_recetas(utensilios: Optional[List[str]] = Query(None, description="Filtrar por utensilios disponibles (ej: ?utensilios=airfryer&utensilios=batidora)")):
    """
    Obtiene el catálogo de recetas. Si se especifican utensilios disponibles,
    filtra y devuelve solo aquellas recetas que el usuario puede cocinar.
    """
    return recipe_service.listar_recetas(utensilios_disponibles=utensilios)


@app.post("/api/v1/recetas", response_model=RecetaSalida)
def crear_receta(receta: RecetaEntrada):
    """
    Guarda una nueva receta y calcula automáticamente de forma determinista
    sus calorías y macronutrientes totales sumando sus ingredientes.
    """
    return recipe_service.crear_receta(receta)


# --- AGENTE INTERACTIVO DE CHAT (TOOL CALLING) ---
@app.post("/api/v1/chat/planificar", response_model=RespuestaChat)
async def chat_planificador(solicitud: SolicitudChat):
    """
    Agente conversacional que utiliza Tool Calling para razonar y realizar
    cálculos matemáticos exactos sobre porciones de alimentos.
    """
    return await agent_service.procesar_chat_agente(solicitud)