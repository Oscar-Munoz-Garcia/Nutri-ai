import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, File, UploadFile, Depends
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

from typing import Optional
import app.services.analytics_service as analytics_service
from app.models.auth import UsuarioRegistro, UsuarioLogin, LoginGoogle, TokenResponse, UsuarioOut
from app.services.auth_service import registrar_usuario, autenticar_usuario, login_google, obtener_usuario_actual
from app.core.config import settings
from app.db.models import UsuarioDB
import app.services.backup_service as backup_service



# Inicializar tablas de SQLite al arrancar la app
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Copia de seguridad diaria de nutri_ai.db mientras el servidor está en marcha (BACKUP_AUTO=0 la desactiva)
    tarea_backup = None
    if os.getenv("BACKUP_AUTO", "1") == "1":
        tarea_backup = asyncio.create_task(backup_service.bucle_backup_diario())
    yield
    if tarea_backup:
        tarea_backup.cancel()


app = FastAPI(
    title="NutriAI Engine API",
    version="1.2.0",
    description="Backend de Ingeniería Nutricional con Visión OCR, Agente IA y Diario de Macros.",
    lifespan=lifespan
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
def obtener_resumen_diario(fecha: Optional[str] = None, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return daily_service.obtener_resumen_diario(current_user.id, fecha=fecha)


@app.post("/api/v1/diario/consumo", response_model=RegistroConsumo, tags=["Diario"])
def registrar_consumo(registro: RegistroConsumo, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return daily_service.registrar_consumo(registro, current_user.id)


@app.put("/api/v1/diario/objetivos", response_model=ObjetivosMacros, tags=["Diario"])
def actualizar_objetivos(objetivos: ObjetivosMacros, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return daily_service.establecer_objetivos(objetivos, current_user.id)


# --- ENDPOINTS DE RECETAS ---
@app.get("/api/v1/recetas", response_model=List[Receta], tags=["Recetas"])
def listar_recetas(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return recipe_service.obtener_todas_las_recetas(current_user.id)


@app.post("/api/v1/recetas", response_model=Receta, tags=["Recetas"])
def guardar_receta(receta: RecetaCrear, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return recipe_service.crear_nueva_receta(receta, current_user.id)


@app.post("/api/v1/recetas/{receta_id}/consumir", tags=["Recetas"])
def consumir_receta(receta_id: str, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    receta = recipe_service.obtener_receta(receta_id, current_user.id)
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    
    registro = RegistroConsumo(
        nombre=receta.nombre,
        calorias=receta.calorias_totales,
        proteinas=receta.proteinas_totales,
        carbohidratos=receta.carbohidratos_totales,
        grasas=receta.grasas_totales
    )
    registro = daily_service.registrar_consumo(registro, current_user.id)
    return {
        "status": "ok",
        "mensaje": f"Receta '{receta.nombre}' registrada en tu diario.",
        "registro": registro
    }


# --- ENDPOINTS DE DESPENSA Y VISION OCR ---
@app.get("/api/v1/despensa", response_model=List[AlimentoPantry], tags=["Despensa"])
def listar_despensa(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return pantry_service.obtener_despensa(current_user.id)


@app.post("/api/v1/despensa", response_model=AlimentoPantry, tags=["Despensa"])
def agregar_alimento_despensa(alimento: AlimentoPantryEntrada, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return pantry_service.agregar_alimento(alimento, current_user.id)


@app.post("/api/v1/alimentos/vision-ocr", response_model=ProductoOCR, tags=["Visión OCR"])
async def procesar_imagen_ocr(file: UploadFile = File(...), current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    contenido = await file.read()
    return await vision_service.analizar_etiqueta_nutricional(contenido, file.filename or "etiqueta.jpg")


# --- ENDPOINT DE CHAT AGENTE ---
@app.post("/api/v1/chat/planificar", response_model=RespuestaChat, tags=["Agente AI"])
async def chat_agente(solicitud: SolicitudChat, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return await agent_service.procesar_chat_agente(solicitud, current_user.id)

# --- ENDPOINTS DE PERFIL DE USUARIO ---
@app.get("/api/v1/perfil", response_model=PerfilUsuario, tags=["Perfil"])
def obtener_perfil(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return profile_service.obtener_perfil(current_user.id)


@app.put("/api/v1/perfil", response_model=PerfilUsuario, tags=["Perfil"])
def actualizar_perfil(datos: PerfilActualizar, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return profile_service.actualizar_perfil(datos, current_user.id)


@app.get("/api/v1/analitica/tendencias", tags=["Analítica"])
def obtener_tendencias(dias: int = 7, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return analytics_service.obtener_tendencias(current_user.id, dias=dias)


@app.delete("/api/v1/diario/consumo/{registro_id}", tags=["Diario"])
def eliminar_consumo(registro_id: int, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    exito = daily_service.eliminar_registro_consumo(registro_id, current_user.id)
    if not exito:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"status": "ok", "message": "Registro eliminado con éxito"}


@app.delete("/api/v1/pantry/{item_id}", tags=["Despensa"])
def eliminar_pantry_item(item_id: str, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    exito = pantry_service.eliminar_item_pantry(item_id, current_user.id)
    if not exito:
        raise HTTPException(status_code=404, detail="Ítem no encontrado en despensa")
    return {"status": "ok", "message": "Ítem eliminado de la despensa"}


@app.post("/api/v1/auth/registro", response_model=TokenResponse, tags=["Autenticación"])
def registro(datos: UsuarioRegistro):
    return registrar_usuario(datos)


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Autenticación"])
def login(datos: UsuarioLogin):
    return autenticar_usuario(datos)


@app.post("/api/v1/auth/google", response_model=TokenResponse, tags=["Autenticación"])
def login_con_google(datos: LoginGoogle):
    return login_google(datos.credential)


@app.get("/api/v1/auth/config", tags=["Autenticación"])
def configuracion_auth():
    # El Client ID de Google es público (va en la página); no es un secreto
    return {"google_client_id": settings.GOOGLE_CLIENT_ID}


@app.get("/api/v1/auth/me", response_model=UsuarioOut, tags=["Autenticación"])
def obtener_mi_perfil(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return current_user