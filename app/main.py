import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, File, Form, UploadFile, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
from app.models.vision import ProductoOCR, AnalisisPlato
from app.models.food import ProductoNutricional
from app.models.shopping import SolicitudListaCompra, ListaCompra
import app.services.openfoodfacts_service as openfoodfacts_service
import app.services.shopping_service as shopping_service

from app.models.profile import PerfilUsuario, PerfilActualizar, CuestionarioRegistro
import app.services.profile_service as profile_service
from app.db.session import init_db

from typing import Optional
import app.services.analytics_service as analytics_service
from app.models.auth import LoginGoogle, TokenResponse, UsuarioOut
from app.services.auth_service import login_google, obtener_usuario_actual, registro_completo, eliminar_cuenta
from app.core.config import settings
from app.db.models import UsuarioDB
import app.services.backup_service as backup_service
from datetime import date
import app.services.export_service as export_service
import app.services.import_service as import_service
import app.services.sheets_service as sheets_service
from app.models.metabolic import PesoEntrada, PesoRegistro, TDEEDinamico, Versus
import app.services.metabolic_service as metabolic_service
from app.models.friends import Amigos, SolicitudAmistadEntrada
import app.services.friends_service as friends_service
import app.services.streak_service as streak_service
import app.services.quicklog_service as quicklog_service
from app.models.quicklog import SolicitudRegistroRapido, RespuestaRegistroRapido



# Inicializar tablas de SQLite al arrancar la app
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Copia de seguridad diaria de nutri_ai.db mientras el servidor está en marcha (BACKUP_AUTO=0 la desactiva)
    tarea_backup = None
    if os.getenv("BACKUP_AUTO", "1") == "1":
        tarea_backup = asyncio.create_task(backup_service.bucle_backup_diario())
    # Cierre de jornada automático en Google Sheets (solo si GOOGLE_SHEETS_HORA_CIERRE está configurado)
    tarea_sheets = sheets_service.iniciar_cierre_automatico()
    yield
    if tarea_backup:
        tarea_backup.cancel()
    if tarea_sheets:
        tarea_sheets.cancel()


app = FastAPI(
    title="NutriAI Engine API",
    version="1.2.0",
    description="Backend de Ingeniería Nutricional con Visión OCR, Agente IA y Diario de Macros.",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


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


@app.get("/api/v1/diario/racha", tags=["Diario"])
def obtener_racha(dias: int = 112, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return streak_service.obtener_racha(current_user.id, dias=dias)


@app.post("/api/v1/diario/interpretar", response_model=RespuestaRegistroRapido, tags=["Diario"])
async def interpretar_registro_rapido(solicitud: SolicitudRegistroRapido, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return await quicklog_service.interpretar_texto(solicitud.texto, current_user.id)


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


@app.post("/api/v1/alimentos/analizar-plato", response_model=AnalisisPlato, tags=["Visión OCR"])
async def analizar_plato(file: UploadFile = File(...), current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    contenido = await file.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="La imagen está vacía.")
    return await vision_service.analizar_plato(contenido, file.filename or "plato.jpg")


@app.get("/api/v1/alimentos/barcode/{codigo}", response_model=ProductoNutricional, tags=["Visión OCR"])
async def buscar_por_codigo_barras(codigo: str, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    codigo = codigo.strip()
    if not codigo.isdigit() or not 8 <= len(codigo) <= 14:
        raise HTTPException(status_code=422, detail="El código de barras debe tener entre 8 y 14 dígitos.")
    producto = await openfoodfacts_service.consultar_open_food_facts(codigo)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado en Open Food Facts.")
    return producto


# --- ENDPOINT DE LISTA DE LA COMPRA ---
@app.post("/api/v1/compra/lista", response_model=ListaCompra, tags=["Lista de la compra"])
def generar_lista_compra(solicitud: SolicitudListaCompra, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return shopping_service.generar_lista_compra(solicitud, usuario_id=current_user.id)


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


@app.post("/api/v1/auth/google", response_model=TokenResponse, tags=["Autenticación"])
def login_con_google(datos: LoginGoogle):
    return login_google(datos.credential)


@app.get("/api/v1/auth/config", tags=["Autenticación"])
def configuracion_auth():
    # El Client ID de Google es público (va en la página); no es un secreto
    return {"google_client_id": settings.GOOGLE_CLIENT_ID}


@app.get("/api/v1/auth/me", response_model=UsuarioOut, tags=["Autenticación"])
def obtener_mi_perfil(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return UsuarioOut(
        id=current_user.id, username=current_user.username, email=current_user.email,
        registro_completo=registro_completo(current_user)
    )


@app.delete("/api/v1/auth/cuenta", tags=["Autenticación"])
def borrar_mi_cuenta(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    """Elimina la cuenta del usuario y todos sus datos (no se puede deshacer)."""
    eliminar_cuenta(current_user.id)
    return {"mensaje": "Cuenta eliminada"}


@app.post("/api/v1/auth/completar-registro", response_model=PerfilUsuario, tags=["Autenticación"])
def completar_registro(datos: CuestionarioRegistro, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    """Cuestionario de alta de un usuario nuevo: nombre, apellidos, edad, peso y objetivo."""
    return profile_service.completar_registro(datos, current_user.id)

# --- ENDPOINTS DE EXCEL, IMPORTACIÓN Y GOOGLE SHEETS ---
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
# --- ENDPOINTS DE TELEMETRÍA METABÓLICA (PESO, TDEE DINÁMICO Y VERSUS) ---
@app.get("/api/v1/peso", response_model=List[PesoRegistro], tags=["Metabolismo"])
def listar_pesos(dias: int = 90, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return metabolic_service.listar_pesos(current_user.id, dias=dias)


@app.post("/api/v1/peso", response_model=PesoRegistro, tags=["Metabolismo"])
def registrar_peso(entrada: PesoEntrada, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    try:
        return metabolic_service.registrar_peso(entrada, current_user.id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Fecha inválida, usa el formato YYYY-MM-DD.")


@app.delete("/api/v1/peso/{peso_id}", tags=["Metabolismo"])
def eliminar_peso(peso_id: int, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    if not metabolic_service.eliminar_peso(peso_id, current_user.id):
        raise HTTPException(status_code=404, detail="Pesaje no encontrado")
    return {"status": "ok", "message": "Pesaje eliminado"}


@app.get("/api/v1/metabolismo/tdee", response_model=TDEEDinamico, tags=["Metabolismo"])
def obtener_tdee_dinamico(dias: int = 28, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return metabolic_service.obtener_tdee_dinamico(current_user.id, dias=max(7, min(dias, 120)))


@app.get("/api/v1/versus", response_model=Versus, tags=["Versus"])
def obtener_versus(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return metabolic_service.obtener_versus(current_user.id)


# --- ENDPOINTS DE AMISTADES (el Versus solo incluye amigos aceptados) ---
@app.get("/api/v1/amigos", response_model=Amigos, tags=["Versus"])
def listar_amigos(current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    return friends_service.listar(current_user.id)


@app.post("/api/v1/amigos/solicitudes", tags=["Versus"])
def enviar_solicitud_amistad(datos: SolicitudAmistadEntrada, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    resultado = friends_service.enviar_solicitud(current_user.id, datos.usuario)
    mensaje = "Ya sois amigos: tenía una solicitud tuya pendiente." if resultado == "aceptada" else "Solicitud enviada."
    return {"status": resultado, "message": mensaje}


@app.post("/api/v1/amigos/solicitudes/{solicitud_id}/aceptar", tags=["Versus"])
def aceptar_solicitud_amistad(solicitud_id: int, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    if not friends_service.aceptar_solicitud(current_user.id, solicitud_id):
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return {"status": "ok", "message": "Solicitud aceptada"}


@app.delete("/api/v1/amigos/solicitudes/{solicitud_id}", tags=["Versus"])
def borrar_solicitud_amistad(solicitud_id: int, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    if not friends_service.borrar_solicitud(current_user.id, solicitud_id):
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return {"status": "ok", "message": "Solicitud eliminada"}


@app.delete("/api/v1/amigos/{amigo_id}", tags=["Versus"])
def eliminar_amigo(amigo_id: int, current_user: UsuarioDB = Depends(obtener_usuario_actual)):
    if not friends_service.eliminar_amigo(current_user.id, amigo_id):
        raise HTTPException(status_code=404, detail="Amigo no encontrado")
    return {"status": "ok", "message": "Amigo eliminado"}
