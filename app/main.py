from fastapi import FastAPI, HTTPException, Request, Response, File, Form, UploadFile, Depends
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
from app.models.auth import UsuarioRegistro, UsuarioLogin, TokenResponse, UsuarioOut
from app.services.auth_service import registrar_usuario, autenticar_usuario, obtener_usuario_actual
from app.db.models import UsuarioDB
from datetime import date
import app.services.export_service as export_service
import app.services.import_service as import_service
import app.services.sheets_service as sheets_service



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

@app.get("/api/v1/diario/resumen", response_model=ResumenDiario, tags=["Diario"])
def obtener_resumen_diario(fecha: Optional[str] = None):
    return daily_service.obtener_resumen_diario(fecha=fecha)


@app.get("/api/v1/analitica/tendencias", tags=["Analítica"])
def obtener_tendencias(dias: int = 7):
    return analytics_service.obtener_tendencias(dias=dias)


@app.delete("/api/v1/diario/consumo/{registro_id}", tags=["Diario"])
def eliminar_consumo(registro_id: int):
    exito = daily_service.eliminar_registro_consumo(registro_id)
    if not exito:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"status": "ok", "message": "Registro eliminado con éxito"}


@app.delete("/api/v1/pantry/{item_id}", tags=["Despensa"])
def eliminar_pantry_item(item_id: str):
    exito = pantry_service.eliminar_item_pantry(item_id)
    if not exito:
        raise HTTPException(status_code=404, detail="Ítem no encontrado en despensa")
    return {"status": "ok", "message": "Ítem eliminado de la despensa"}


@app.post("/api/v1/auth/registro", response_model=TokenResponse, tags=["Autenticación"])
def registro(datos: UsuarioRegistro):
    return registrar_usuario(datos)


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Autenticación"])
def login(datos: UsuarioLogin):
    return autenticar_usuario(datos)


@app.get("/api/v1/auth/me", response_model=UsuarioOut, tags=["Autenticación"])
def obtener_mi_perfil(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return current_user

# --- ENDPOINTS DE EXCEL, IMPORTACIÓN Y GOOGLE SHEETS ---
@app.on_event("startup")
async def arrancar_cierre_automatico_sheets():
    sheets_service.iniciar_cierre_automatico()


@app.get("/api/v1/exportar/excel", tags=["Excel"])
def exportar_excel(anio: Optional[int] = None, mes: Optional[int] = None,
                   current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    hoy = date.today()
    anio, mes = anio or hoy.year, mes or hoy.month
    try:
        contenido = export_service.generar_reporte_mensual(current_user.id, anio, mes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    nombre = f"nutriai_{current_user.username}_{anio}-{mes:02d}.xlsx"
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@app.post("/api/v1/importar", tags=["Excel"])
async def importar_archivo(file: UploadFile = File(...), tipo: Optional[str] = Form(None),
                           current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    contenido = await file.read()
    if len(contenido) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera 5 MB.")
    try:
        return import_service.importar_archivo(contenido, file.filename or "", current_user.id, tipo or None)
    except import_service.ErrorImportacion as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/sheets/estado", tags=["Google Sheets"])
def estado_sheets(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return sheets_service.estado()


@app.post("/api/v1/sheets/cerrar-jornada", tags=["Google Sheets"])
async def cerrar_jornada_sheets(fecha: Optional[str] = None,
                                current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    try:
        return await sheets_service.enviar_resumen(current_user, fecha)
    except sheets_service.SheetsNoConfigurado as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo enviar a Google Sheets: {exc}")
