from datetime import date, timedelta
from typing import List, Dict, Any
from app.db.session import SessionLocal
from app.db.models import RegistroConsumoDB, PerfilDB, PesoHistorialDB
from app.services import plan_service


def obtener_tendencias(usuario_id: int, dias: int = 7) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        hoy = date.today()
        fechas = [(hoy - timedelta(days=i)).isoformat() for i in range(dias - 1, -1, -1)]

        pdb = db.query(PerfilDB).filter(PerfilDB.usuario_id == usuario_id).first()
        # Meta de cada día según su plan de nutrición; meta_calorias es la de hoy
        planes = plan_service.planes_por_fecha(db, usuario_id, fechas)
        metas_calorias = [planes[f].calorias_objetivo for f in fechas]
        meta_calorias = metas_calorias[-1] if metas_calorias else (pdb.calorias_objetivo if pdb else 2200.0)

        # Obtener consumos de las fechas solicitadas
        registros = db.query(RegistroConsumoDB).filter(
            RegistroConsumoDB.usuario_id == usuario_id,
            RegistroConsumoDB.fecha.in_(fechas)
        ).all()

        # Agrupar por fecha
        calorias_por_dia = {f: 0.0 for f in fechas}
        proteinas_por_dia = {f: 0.0 for f in fechas}

        for r in registros:
            if r.fecha in calorias_por_dia:
                calorias_por_dia[r.fecha] += r.calorias
                proteinas_por_dia[r.fecha] += r.proteinas

        # Formatear etiquetas legibles (ej: "21 Oct")
        etiquetas = []
        for f in fechas:
            d = date.fromisoformat(f)
            etiquetas.append(d.strftime("%d %b"))

        # Historial de Peso
        pesos_db = db.query(PesoHistorialDB).filter(
            PesoHistorialDB.usuario_id == usuario_id,
            PesoHistorialDB.fecha.in_(fechas)
        ).all()
        peso_map = {p.fecha: p.peso_kg for p in pesos_db}
        pesos = [peso_map.get(f, pdb.peso_kg if pdb else 75.0) for f in fechas]

        # Promedios
        promedio_calorias = round(sum(calorias_por_dia.values()) / max(1, len(fechas)), 1)
        promedio_proteinas = round(sum(proteinas_por_dia.values()) / max(1, len(fechas)), 1)

        return {
            "fechas": fechas,
            "etiquetas": etiquetas,
            "meta_calorias": meta_calorias,
            "metas_calorias": metas_calorias,
            "calorias": [round(v, 1) for v in calorias_por_dia.values()],
            "proteinas": [round(v, 1) for v in proteinas_por_dia.values()],
            "pesos": pesos,
            "promedio_calorias": promedio_calorias,
            "promedio_proteinas": promedio_proteinas
        }
    finally:
        db.close()