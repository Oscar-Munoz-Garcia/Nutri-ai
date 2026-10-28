import json
import uuid
from typing import List, Optional
from app.models.recipe import Receta, RecetaCrear
from app.db.session import SessionLocal
from app.db.models import RecetaDB


def _cargar_lista_json(valor: Optional[str]) -> list:
    if not valor:
        return []
    try:
        datos = json.loads(valor)
        return datos if isinstance(datos, list) else []
    except (ValueError, TypeError):
        # Formato antiguo: utensilios separados por comas
        return [v.strip() for v in valor.split(",") if v.strip()]


def _a_modelo(r: RecetaDB) -> Receta:
    return Receta(
        id=r.id,
        nombre=r.nombre,
        descripcion=r.descripcion or "",
        calorias_totales=r.calorias_totales,
        proteinas_totales=r.proteinas_totales,
        carbohidratos_totales=r.carbohidratos_totales,
        grasas_totales=r.grasas_totales,
        tiempo_preparacion_min=r.tiempo_preparacion_min,
        utensilios_necesarios=_cargar_lista_json(r.utensilios_necesarios),
        ingredientes=_cargar_lista_json(r.ingredientes),
        pasos=_cargar_lista_json(r.pasos)
    )


def obtener_todas_las_recetas(usuario_id: int) -> List[Receta]:
    db = SessionLocal()
    try:
        recetas = db.query(RecetaDB).filter(RecetaDB.usuario_id == usuario_id).order_by(RecetaDB.nombre).all()
        return [_a_modelo(r) for r in recetas]
    finally:
        db.close()


def obtener_receta(receta_id: str, usuario_id: int) -> Optional[Receta]:
    db = SessionLocal()
    try:
        r = db.query(RecetaDB).filter(RecetaDB.id == str(receta_id), RecetaDB.usuario_id == usuario_id).first()
        return _a_modelo(r) if r else None
    finally:
        db.close()


def crear_nueva_receta(datos: RecetaCrear, usuario_id: int) -> Receta:
    db = SessionLocal()
    try:
        nueva = RecetaDB(
            id="rec_" + str(uuid.uuid4())[:8],
            usuario_id=usuario_id,
            nombre=datos.nombre,
            descripcion=datos.descripcion or "",
            calorias_totales=datos.calorias_totales,
            proteinas_totales=datos.proteinas_totales,
            carbohidratos_totales=datos.carbohidratos_totales,
            grasas_totales=datos.grasas_totales,
            tiempo_preparacion_min=datos.tiempo_preparacion_min,
            utensilios_necesarios=json.dumps(datos.utensilios_necesarios, ensure_ascii=False),
            ingredientes=json.dumps([i.model_dump() for i in (datos.ingredientes or [])], ensure_ascii=False),
            pasos=json.dumps(datos.pasos or [], ensure_ascii=False)
        )
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        return _a_modelo(nueva)
    finally:
        db.close()


def listar_recetas(usuario_id: int, utensilios_disponibles: Optional[List[str]] = None) -> List[Receta]:
    """Recetas del usuario cuyos utensilios requeridos están todos disponibles."""
    recetas = obtener_todas_las_recetas(usuario_id)
    if not utensilios_disponibles:
        return recetas

    utensilios_usuario = {u.strip().lower() for u in utensilios_disponibles}
    return [
        r for r in recetas
        if {u.strip().lower() for u in r.utensilios_necesarios}.issubset(utensilios_usuario)
    ]
