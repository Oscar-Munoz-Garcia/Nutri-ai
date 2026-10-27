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
from app.models.vision import ProductoOCR, AnalisisPlato
from app.models.food import ProductoNutricional
from app.models.shopping import SolicitudListaCompra, ListaCompra
import app.services.openfoodfacts_service as openfoodfacts_service
import app.services.shopping_service as shopping_service

from app.models.profile import PerfilUsuario, PerfilActualizar
import app.services.profile_service as profile_service
from app.db.session import init_db

from typing import Optional
import app.services.analytics_service as analytics_service
from app.models.auth import UsuarioRegistro, UsuarioLogin, TokenResponse, UsuarioOut
from app.services.auth_service import registrar_usuario, autenticar_usuario, obtener_usuario_actual
from app.db.models import UsuarioDB



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