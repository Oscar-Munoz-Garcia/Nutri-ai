from datetime import date, timedelta
from typing import Dict, Any, Optional
from app.db.session import SessionLocal
from app.db.models import RegistroConsumoDB
from app.services.daily_service import obtener_o_crear_perfil_db

# Margen aceptado alrededor de la meta calórica y mínimo de proteína para contar el día como cumplido
MARGEN_CALORIAS = 0.10
MINIMO_PROTEINAS = 0.90


def _evaluar_dia(calorias: float, proteinas: float, meta_cal: float, meta_prot: float, hay_registros: bool) -> Dict[str, Any]:
    cumple_cal = meta_cal > 0 and abs(calorias - meta_cal) <= meta_cal * MARGEN_CALORIAS
    cumple_prot = meta_prot > 0 and proteinas >= meta_prot * MINIMO_PROTEINAS

    if not hay_registros:
        nivel = 0
    elif cumple_cal and cumple_prot:
        nivel = 3
    elif cumple_cal or cumple_prot:
        nivel = 2
    else:
        nivel = 1

    return {"cumple_calorias": cumple_cal, "cumple_proteinas": cumple_prot, "nivel": nivel}


def obtener_racha(usuario_id: int, dias: int = 112, hoy: Optional[date] = None) -> Dict[str, Any]:
    """Calendario de constancia: un día cuenta como cumplido si las calorías quedan
    dentro de ±10% de la meta y las proteínas llegan al 90% de la meta."""
    dias = max(7, min(dias, 371))
    hoy = hoy or date.today()
    # Empezar en lunes para que la cuadrícula semanal quede alineada
    inicio = hoy - timedelta(days=dias - 1)
    inicio -= timedelta(days=inicio.weekday())

    db = SessionLocal()
    try:
        pdb = obtener_o_crear_perfil_db(db, usuario_id)
        meta_cal = pdb.calorias_objetivo
        meta_prot = pdb.proteinas_objetivo

        consulta = db.query(RegistroConsumoDB).filter(
            RegistroConsumoDB.usuario_id == usuario_id,
            RegistroConsumoDB.fecha >= inicio.isoformat(),
            RegistroConsumoDB.fecha <= hoy.isoformat()
        )

        totales: Dict[str, Dict[str, float]] = {}
        for r in consulta.all():
            t = totales.setdefault(r.fecha, {"calorias": 0.0, "proteinas": 0.0})
            t["calorias"] += r.calorias or 0.0
            t["proteinas"] += r.proteinas or 0.0

        lista_dias = []
        d = inicio
        while d <= hoy:
            f = d.isoformat()
            t = totales.get(f, {"calorias": 0.0, "proteinas": 0.0})
            evaluacion = _evaluar_dia(t["calorias"], t["proteinas"], meta_cal, meta_prot, f in totales)
            lista_dias.append({
                "fecha": f,
                "calorias": round(t["calorias"], 1),
                "proteinas": round(t["proteinas"], 1),
                **evaluacion
            })
            d += timedelta(days=1)

        # Mejor racha dentro del rango
        mejor = actual_tmp = 0
        for dia in lista_dias:
            actual_tmp = actual_tmp + 1 if dia["nivel"] == 3 else 0
            mejor = max(mejor, actual_tmp)

        # Racha actual: hoy aún está en curso, así que si no está cumplido se cuenta desde ayer
        racha_actual = 0
        pendientes = list(reversed(lista_dias))
        if pendientes and pendientes[0]["nivel"] != 3:
            pendientes = pendientes[1:]
        for dia in pendientes:
            if dia["nivel"] != 3:
                break
            racha_actual += 1

        return {
            "desde": inicio.isoformat(),
            "hasta": hoy.isoformat(),
            "meta_calorias": meta_cal,
            "meta_proteinas": meta_prot,
            "racha_actual": racha_actual,
            "mejor_racha": mejor,
            "dias_cumplidos": sum(1 for x in lista_dias if x["nivel"] == 3),
            "dias_registrados": sum(1 for x in lista_dias if x["nivel"] > 0),
            "dias": lista_dias
        }
    finally:
        db.close()
