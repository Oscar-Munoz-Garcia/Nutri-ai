from fastapi import FastAPI, HTTPException, Request, Response, File, UploadFile
from fastapi.responses import HTMLResponse
from typing import List, Optional
from pathlib import Path

from app.models.recipe import Receta, RecetaCrear
from app.models.daily import ObjetivosMacros, RegistroConsumo, ResumenDiario
from app.models.chat import SolicitudChat, RespuestaChat
import app.services.recipe_service as recipe_service
import app.services.daily_service as daily_service
import app.services.pantry_service as pantry_service
import app.services.vision_service as vision_service
import app.services.agent_service as agent_service
from app.models.pantry import AlimentoPantry, AlimentoPantryEntrada
from app.models.vision import ProductoOCR

from app.models.profile import PerfilUsuario, PerfilActualizar
import app.services.profile_service as profile_service
from app.db.session import init_db
# Inicializar tablas de SQLite al arrancar la app
init_db()
app = FastAPI(
    title="NutriAI Engine API",
    version="1.2.0",
    description="Backend de Ingeniería Nutricional con Visión OCR, Agente IA y Diario de Macros."
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def get_dashboard():
    template_path = Path(__file__).parent / "templates" / "index.html"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Plantilla no encontrada.")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/manifest.json", include_in_schema=False)
def get_manifest():
    manifest_path = Path(__file__).parent / "templates" / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest no encontrado.")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return Response(content=f.read(), media_type="application/json")


# --- ENDPOINTS DE DIARIO Y MACROS ---
@app.get("/api/v1/diario/resumen", response_model=ResumenDiario, tags=["Diario"])
def obtener_resumen_diario():
    return daily_service.obtener_resumen_diario()


@app.post("/api/v1/diario/consumo", response_model=RegistroConsumo, tags=["Diario"])
def registrar_consumo(registro: RegistroConsumo):
    return daily_service.registrar_consumo(registro)


@app.put("/api/v1/diario/objetivos", response_model=ObjetivosMacros, tags=["Diario"])
def actualizar_objetivos(objetivos: ObjetivosMacros):
    return daily_service.establecer_objetivos(objetivos)


# --- ENDPOINTS DE RECETAS ---
@app.get("/api/v1/recetas", response_model=List[Receta], tags=["Recetas"])
def listar_recetas():
    return recipe_service.obtener_todas_las_recetas()


@app.post("/api/v1/recetas", response_model=Receta, tags=["Recetas"])
def guardar_receta(receta: RecetaCrear):
    return recipe_service.crear_nueva_receta(receta)


@app.post("/api/v1/recetas/{receta_id}/consumir", tags=["Recetas"])
def consumir_receta(receta_id: str):
    recetas = recipe_service.obtener_todas_las_recetas()
    receta = next((r for r in recetas if str(r.id) == str(receta_id)), None)
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    
    registro = RegistroConsumo(
        nombre=receta.nombre,
        calorias=receta.calorias_totales,
        proteinas=receta.proteinas_totales,
        carbohidratos=receta.carbohidratos_totales,
        grasas=receta.grasas_totales
    )
    daily_service.registrar_consumo(registro)
    return {
        "status": "ok",
        "mensaje": f"Receta '{receta.nombre}' registrada en tu diario.",
        "registro": registro
    }


# --- ENDPOINTS DE DESPENSA Y VISION OCR ---
@app.get("/api/v1/despensa", response_model=List[AlimentoPantry], tags=["Despensa"])
def listar_despensa():
    return pantry_service.obtener_despensa()


@app.post("/api/v1/despensa", response_model=AlimentoPantry, tags=["Despensa"])
def agregar_alimento_despensa(alimento: AlimentoPantryEntrada):
    return pantry_service.agregar_alimento(alimento)


@app.post("/api/v1/alimentos/vision-ocr", response_model=ProductoOCR, tags=["Visión OCR"])
async def procesar_imagen_ocr(file: UploadFile = File(...)):
    contenido = await file.read()
    return await vision_service.analizar_etiqueta_nutricional(contenido, file.filename or "etiqueta.jpg")


# --- ENDPOINT DE CHAT AGENTE ---
@app.post("/api/v1/chat/planificar", response_model=RespuestaChat, tags=["Agente AI"])
async def chat_agente(solicitud: SolicitudChat):
    return await agent_service.procesar_chat_agente(solicitud)

# --- ENDPOINTS DE PERFIL DE USUARIO ---
@app.get("/api/v1/perfil", response_model=PerfilUsuario, tags=["Perfil"])
def obtener_perfil():
    return profile_service.obtener_perfil()


@app.put("/api/v1/perfil", response_model=PerfilUsuario, tags=["Perfil"])
def actualizar_perfil(datos: PerfilActualizar):
    return profile_service.actualizar_perfil(datos)