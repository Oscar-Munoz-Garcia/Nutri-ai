import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, File, UploadFile, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response

from app.core.config import settings
from app.models.user import PerfilUsuario, ObjetivoMacros
from app.models.food import ProductoNutricional
from app.models.pantry import ItemDespensa, RegistroComidaEntrada, RegistroComidaSalida, ResumenDiarioMacros
from app.models.recipe import RecetaEntrada, RecetaSalida
from app.models.recommendation import SolicitudRecomendacion, RecomendacionResultado
from app.models.chat import SolicitudChat, RespuestaChat

from app.services.macro_service import calcular_objetivo_macros
from app.services.openfoodfacts_service import consultar_open_food_facts
from app.services import pantry_service
from app.services.vision_service import analizar_etiqueta_imagen
from app.services import recipe_service
from app.services import recommendation_service
import app.services.agent_service as agent_service

from app.models.recipe import Receta, RecetaCrear
import app.services.recipe_service as recipe_service

app = FastAPI(title=settings.PROJECT_NAME)


# --- DASHBOARD Y DOCUMENTACIÓN ---
@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def ver_dashboard():
    """Servicio de la interfaz web del Dashboard NutriAI Studio."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Plantilla Dashboard no encontrada.")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


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
def listar_recetas(utensilios: Optional[List[str]] = Query(None)):
    return recipe_service.listar_recetas(utensilios_disponibles=utensilios)


@app.post("/api/v1/recetas", response_model=RecetaSalida)
def crear_receta(receta: RecetaEntrada):
    return recipe_service.crear_receta(receta)


# --- RECOMENDADOR NUTRICIONAL INTELIGENTE ---
@app.post("/api/v1/recomendaciones/sugerir", response_model=List[RecomendacionResultado])
def sugerir_recetas(solicitud: SolicitudRecomendacion):
    return recommendation_service.obtener_sugerencias_recetas(solicitud)


# --- AGENTE INTERACTIVO DE CHAT (TOOL CALLING) ---
@app.post("/api/v1/chat/planificar", response_model=RespuestaChat)
async def chat_planificador(solicitud: SolicitudChat):
    return await agent_service.procesar_chat_agente(solicitud)

@app.get("/manifest.json", include_in_schema=False)
def get_manifest():
    """Sirve el manifiesto de la aplicación PWA para móviles."""
    manifest_path = Path(__file__).parent / "templates" / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest no encontrado.")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return Response(content=f.read(), media_type="application/json")


@app.get("/api/v1/recetas", response_model=List[Receta], tags=["Recetas"])
def listar_recetas():
    return recipe_service.obtener_todas_las_recetas()


@app.post("/api/v1/recetas", response_model=Receta, tags=["Recetas"])
def guardar_receta(receta: RecetaCrear):
    return recipe_service.crear_nueva_receta(receta)