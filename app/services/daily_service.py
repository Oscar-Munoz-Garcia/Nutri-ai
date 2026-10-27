from datetime import date
from typing import Optional
from app.models.daily import ObjetivosMacros, RegistroConsumo, ResumenDiario
from app.db.session import SessionLocal
from app.db.models import RegistroConsumoDB, PerfilDB


def _fecha_hoy() -> str:
    return date.today().isoformat()


def obtener_o_crear_perfil_db(db, usuario_id: int) -> PerfilDB:
    """Devuelve el perfil del usuario, creándolo con valores por defecto si aún no existe."""
    pdb = db.query(PerfilDB).filter(PerfilDB.usuario_id == usuario_id).first()
    if not pdb:
        pdb = PerfilDB(usuario_id=usuario_id, nombre="Usuario")
        db.add(pdb)
        db.commit()
        db.refresh(pdb)
    return pdb


def establecer_objetivos(objetivos: ObjetivosMacros, usuario_id: int) -> ObjetivosMacros:
    db = SessionLocal()
    try:
        pdb = obtener_o_crear_perfil_db(db, usuario_id)
        pdb.calorias_objetivo = objetivos.calorias_objetivo
        pdb.proteinas_objetivo = objetivos.proteinas_objetivo
        pdb.carbohidratos_objetivo = objetivos.carbohidratos_objetivo
        pdb.grasas_objetivo = objetivos.grasas_objetivo
        db.commit()
        return objetivos
    finally:
        db.close()


def registrar_consumo(registro: RegistroConsumo, usuario_id: int, fecha: Optional[str] = None) -> RegistroConsumo:
    fecha_target = fecha or _fecha_hoy()
    db = SessionLocal()
    try:
        nuevo = RegistroConsumoDB(
            usuario_id=usuario_id,
            fecha=fecha_target,
            nombre=registro.nombre,
            calorias=registro.calorias,
            proteinas=registro.proteinas,
            carbohidratos=registro.carbohidratos,
            grasas=registro.grasas
        )
        db.add(nuevo)
        db.commit()
        return registro.model_copy(update={"id": nuevo.id})
    finally:
        db.close()


def eliminar_registro_consumo(registro_id: int, usuario_id: int) -> bool:
    db = SessionLocal()
    try:
        registro = db.query(RegistroConsumoDB).filter(
            RegistroConsumoDB.id == registro_id,
            RegistroConsumoDB.usuario_id == usuario_id
        ).first()
        if registro:
            db.delete(registro)
            db.commit()
            return True
        return False
    finally:
        db.close()


def obtener_resumen_diario(usuario_id: int, fecha: Optional[str] = None) -> ResumenDiario:
    fecha_target = fecha or _fecha_hoy()
    db = SessionLocal()
    try:
        pdb = obtener_o_crear_perfil_db(db, usuario_id)

        objetivos = ObjetivosMacros(
            calorias_objetivo=pdb.calorias_objetivo,
            proteinas_objetivo=pdb.proteinas_objetivo,
            carbohidratos_objetivo=pdb.carbohidratos_objetivo,
            grasas_objetivo=pdb.grasas_objetivo
        )

        registros_db = db.query(RegistroConsumoDB).filter(
            RegistroConsumoDB.usuario_id == usuario_id,
            RegistroConsumoDB.fecha == fecha_target
        ).all()
        registros = [
            RegistroConsumo(
                id=r.id,
                nombre=r.nombre,
                calorias=r.calorias,
                proteinas=r.proteinas,
                carbohidratos=r.carbohidratos,
                grasas=r.grasas
            ) for r in registros_db
        ]

        cal_tot = sum(r.calorias for r in registros)
        prot_tot = sum(r.proteinas for r in registros)
        carb_tot = sum(r.carbohidratos for r in registros)
        gras_tot = sum(r.grasas for r in registros)

        return ResumenDiario(
            calorias_totales=round(cal_tot, 1),
            proteinas_totales=round(prot_tot, 1),
            carbohidratos_totales=round(carb_tot, 1),
            grasas_totales=round(gras_tot, 1),
            objetivos=objetivos,
            calorias_restantes=round(max(0.0, objetivos.calorias_objetivo - cal_tot), 1),
            proteinas_restantes=round(max(0.0, objetivos.proteinas_objetivo - prot_tot), 1),
            carbohidratos_restantes=round(max(0.0, objetivos.carbohidratos_objetivo - carb_tot), 1),
            grasas_restantes=round(max(0.0, objetivos.grasas_objetivo - gras_tot), 1),
            registros=registros
        )
    finally:
        db.close()
