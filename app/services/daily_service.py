from typing import List
from app.models.daily import ObjetivosMacros, RegistroConsumo, ResumenDiario
from app.db.session import SessionLocal
from app.db.models import RegistroConsumoDB, PerfilDB


def establecer_objetivos(objetivos: ObjetivosMacros) -> ObjetivosMacros:
    db = SessionLocal()
    try:
        pdb = db.query(PerfilDB).filter(PerfilDB.id == 1).first()
        if not pdb:
            pdb = PerfilDB(id=1)
            db.add(pdb)

        pdb.calorias_objetivo = objetivos.calorias_objetivo
        pdb.proteinas_objetivo = objetivos.proteinas_objetivo
        pdb.carbohidratos_objetivo = objetivos.carbohidratos_objetivo
        pdb.grasas_objetivo = objetivos.grasas_objetivo

        db.commit()
        return objetivos
    finally:
        db.close()


def registrar_consumo(registro: RegistroConsumo) -> RegistroConsumo:
    db = SessionLocal()
    try:
        nuevo = RegistroConsumoDB(
            nombre=registro.nombre,
            calorias=registro.calorias,
            proteinas=registro.proteinas,
            carbohidratos=registro.carbohidratos,
            grasas=registro.grasas
        )
        db.add(nuevo)
        db.commit()
        return registro
    finally:
        db.close()


def obtener_resumen_diario() -> ResumenDiario:
    db = SessionLocal()
    try:
        pdb = db.query(PerfilDB).filter(PerfilDB.id == 1).first()
        if not pdb:
            pdb = PerfilDB(id=1)
            db.add(pdb)
            db.commit()
            db.refresh(pdb)

        objetivos = ObjetivosMacros(
            calorias_objetivo=pdb.calorias_objetivo,
            proteinas_objetivo=pdb.proteinas_objetivo,
            carbohidratos_objetivo=pdb.carbohidratos_objetivo,
            grasas_objetivo=pdb.grasas_objetivo
        )

        registros_db = db.query(RegistroConsumoDB).all()
        registros = [
            RegistroConsumo(
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