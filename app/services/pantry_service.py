import uuid
from datetime import date
from typing import List
from app.models.pantry import AlimentoPantry, AlimentoPantryEntrada
from app.db.session import SessionLocal
from app.db.models import PantryDB


def _a_modelo(item: PantryDB) -> AlimentoPantry:
    return AlimentoPantry(
        id=item.id,
        nombre=item.nombre,
        cantidad_gramos=item.cantidad_gramos,
        calorias_100g=item.calorias_100g,
        proteinas_100g=item.proteinas_100g,
        carbohidratos_100g=item.carbohidratos_100g,
        grasas_100g=item.grasas_100g
    )


def obtener_despensa(usuario_id: int) -> List[AlimentoPantry]:
    db = SessionLocal()
    try:
        items = db.query(PantryDB).filter(PantryDB.usuario_id == usuario_id).order_by(PantryDB.nombre).all()
        return [_a_modelo(i) for i in items]
    finally:
        db.close()


def agregar_alimento(alimento: AlimentoPantryEntrada, usuario_id: int) -> AlimentoPantry:
    """Añade un alimento a la despensa del usuario. Si ya existe uno con el mismo nombre, suma la cantidad."""
    db = SessionLocal()
    try:
        nombre_normalizado = alimento.nombre.strip().lower()
        existentes = db.query(PantryDB).filter(PantryDB.usuario_id == usuario_id).all()
        item = next((i for i in existentes if (i.nombre or "").strip().lower() == nombre_normalizado), None)

        if item:
            item.cantidad_gramos = (item.cantidad_gramos or 0.0) + alimento.cantidad_gramos
        else:
            item = PantryDB(
                id=str(uuid.uuid4())[:8],
                usuario_id=usuario_id,
                nombre=alimento.nombre.strip(),
                cantidad_gramos=alimento.cantidad_gramos,
                fecha_registro=date.today().isoformat()
            )
            db.add(item)

        item.calorias_100g = alimento.calorias_100g
        item.proteinas_100g = alimento.proteinas_100g
        item.carbohidratos_100g = alimento.carbohidratos_100g
        item.grasas_100g = alimento.grasas_100g

        db.commit()
        db.refresh(item)
        return _a_modelo(item)
    finally:
        db.close()


def eliminar_item_pantry(item_id: str, usuario_id: int) -> bool:
    db = SessionLocal()
    try:
        item = db.query(PantryDB).filter(PantryDB.id == item_id, PantryDB.usuario_id == usuario_id).first()
        if item:
            db.delete(item)
            db.commit()
            return True
        return False
    finally:
        db.close()
