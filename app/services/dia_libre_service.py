"""Días libres: fechas en las que el usuario come fuera. No cuentan para las metas ni para la racha.
Cada usuario elige en su perfil cuántos puede marcar por semana (de lunes a domingo)."""
from datetime import date, timedelta
from typing import List, Optional, Set

from app.db.models import DiaLibreDB, PerfilDB
from app.db.session import SessionLocal
from app.models.dia_libre import DiasLibresSemana

LIMITE_POR_DEFECTO = 1


class LimiteDiasLibres(ValueError):
    pass


def fechas_libres(db, usuario_id: int, fechas: List[str]) -> Set[str]:
    if not fechas:
        return set()
    filas = db.query(DiaLibreDB.fecha).filter(
        DiaLibreDB.usuario_id == usuario_id,
        DiaLibreDB.fecha >= min(fechas),
        DiaLibreDB.fecha <= max(fechas)
    ).all()
    return {f for (f,) in filas} & set(fechas)


def es_libre(db, usuario_id: int, fecha: str) -> bool:
    return bool(fechas_libres(db, usuario_id, [fecha]))


def _limite(db, usuario_id: int) -> int:
    perfil = db.query(PerfilDB).filter(PerfilDB.usuario_id == usuario_id).first()
    if not perfil or perfil.dias_libres_semana is None:
        return LIMITE_POR_DEFECTO
    return perfil.dias_libres_semana


def _semana(db, usuario_id: int, dia: date) -> DiasLibresSemana:
    lunes = dia - timedelta(days=dia.weekday())
    fechas = [(lunes + timedelta(days=i)).isoformat() for i in range(7)]
    libres = sorted(fechas_libres(db, usuario_id, fechas))
    return DiasLibresSemana(semana_inicio=fechas[0], semana_fin=fechas[-1],
                            limite=_limite(db, usuario_id), usados=len(libres), fechas=libres)


def obtener_semana(usuario_id: int, fecha: Optional[str] = None) -> DiasLibresSemana:
    db = SessionLocal()
    try:
        return _semana(db, usuario_id, date.fromisoformat(fecha) if fecha else date.today())
    finally:
        db.close()


def marcar(usuario_id: int, fecha: str, libre: bool) -> DiasLibresSemana:
    """Marca o desmarca un día libre. Si la semana ya tiene todos los permitidos, lanza LimiteDiasLibres."""
    dia = date.fromisoformat(fecha)
    db = SessionLocal()
    try:
        fila = db.query(DiaLibreDB).filter(DiaLibreDB.usuario_id == usuario_id, DiaLibreDB.fecha == fecha).first()
        if libre and not fila:
            semana = _semana(db, usuario_id, dia)
            if semana.usados >= semana.limite:
                raise LimiteDiasLibres(
                    f"Ya has llegado a tu límite de días libres esta semana ({semana.limite}). Puedes cambiarlo en tu perfil."
                )
            db.add(DiaLibreDB(usuario_id=usuario_id, fecha=fecha))
        elif not libre and fila:
            db.delete(fila)
        db.commit()
        return _semana(db, usuario_id, dia)
    finally:
        db.close()
