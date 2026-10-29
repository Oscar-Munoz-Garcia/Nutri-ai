"""Planes de nutrición: cada usuario tiene varios (p. ej. entrenamiento / descanso), los asigna por día
de la semana y puede cambiar el plan de una fecha concreta. El plan principal es el del perfil."""
import json
from datetime import date, timedelta
from typing import Dict, List, Optional

from app.db.models import PerfilDB, PlanFechaDB, PlanNutricionDB
from app.db.session import SessionLocal
from app.models.plan import AsignacionSemana, Plan, PlanDelDia, PlanEntrada, PlanesUsuario

NOMBRE_PLAN_PRINCIPAL = "Plan principal"
CAMPOS_METAS = ("calorias_objetivo", "proteinas_objetivo", "carbohidratos_objetivo", "grasas_objetivo")

# Reparto de comidas propuesto según cuántas se hacen al día (el usuario puede renombrarlas)
COMIDAS_SUGERIDAS = {
    1: ["Comida"],
    2: ["Comida", "Cena"],
    3: ["Desayuno", "Comida", "Cena"],
    4: ["Desayuno", "Comida", "Merienda", "Cena"],
    5: ["Desayuno", "Almuerzo", "Comida", "Merienda", "Cena"],
    6: ["Desayuno", "Almuerzo", "Comida", "Merienda", "Cena", "Recena"],
    7: ["Desayuno", "Almuerzo", "Comida", "Pre-entreno", "Post-entreno", "Cena", "Recena"],
    8: ["Desayuno", "Almuerzo", "Comida", "Merienda", "Pre-entreno", "Post-entreno", "Cena", "Recena"],
}
COMIDAS_POR_DEFECTO = COMIDAS_SUGERIDAS[3]


class PlanNoValido(ValueError):
    pass


def _dias(plan: PlanNutricionDB) -> List[int]:
    return sorted(int(d) for d in (plan.dias_semana or "").split(",") if d.strip().isdigit())


def comidas_sugeridas(numero: int) -> List[str]:
    return list(COMIDAS_SUGERIDAS.get(numero, COMIDAS_POR_DEFECTO))


def comidas_de(plan: Optional[PlanNutricionDB]) -> List[str]:
    """Comidas del plan en orden; los planes creados antes de poder elegirlas tienen las 3 de siempre."""
    try:
        comidas = json.loads(plan.comidas) if plan is not None and plan.comidas else None
    except ValueError:
        comidas = None
    return [str(c) for c in comidas] if comidas else list(COMIDAS_POR_DEFECTO)


def _poner_comidas(plan: PlanNutricionDB, comidas: Optional[List[str]]) -> None:
    if comidas:
        plan.comidas = json.dumps(comidas, ensure_ascii=False)


def _copiar_metas(origen, destino) -> None:
    for campo in CAMPOS_METAS:
        setattr(destino, campo, getattr(origen, campo))


def _plan_desde_perfil(usuario_id: int, perfil: Optional[PerfilDB]) -> PlanNutricionDB:
    plan = PlanNutricionDB(usuario_id=usuario_id, nombre=NOMBRE_PLAN_PRINCIPAL, es_principal=1,
                           dias_semana="0,1,2,3,4,5,6")
    _copiar_metas(perfil or PerfilDB(calorias_objetivo=2200.0, proteinas_objetivo=160.0,
                                     carbohidratos_objetivo=210.0, grasas_objetivo=70.0), plan)
    return plan


def _planes(db, usuario_id: int, crear: bool) -> List[PlanNutricionDB]:
    """Planes del usuario, el principal primero. Si aún no tiene ninguno, el principal sale del perfil
    (cuestionario de alta o metas que ya tenía); con crear=False no se guarda en la base de datos."""
    planes = db.query(PlanNutricionDB).filter(PlanNutricionDB.usuario_id == usuario_id).order_by(
        PlanNutricionDB.es_principal.desc(), PlanNutricionDB.id).all()
    if planes:
        return planes
    perfil = db.query(PerfilDB).filter(PerfilDB.usuario_id == usuario_id).first()
    principal = _plan_desde_perfil(usuario_id, perfil)
    if crear:
        db.add(principal)
        db.commit()
        db.refresh(principal)
    return [principal]


def _plan_semanal(planes: List[PlanNutricionDB]) -> Dict[int, PlanNutricionDB]:
    """Plan de cada día de la semana; un día sin plan asignado usa el principal."""
    principal = planes[0]
    semana = {d: principal for d in range(7)}
    for plan in planes:
        if plan is principal:
            continue
        for d in _dias(plan):
            semana[d] = plan
    return semana


def planes_por_fecha(db, usuario_id: int, fechas: List[str], crear: bool = False) -> Dict[str, PlanNutricionDB]:
    """Plan que se aplica en cada fecha: el cambiado a mano si lo hay, si no el del día de la semana."""
    planes = _planes(db, usuario_id, crear)
    por_id = {p.id: p for p in planes}
    semana = _plan_semanal(planes)
    cambios = {}
    if fechas and por_id:
        filas = db.query(PlanFechaDB).filter(
            PlanFechaDB.usuario_id == usuario_id, PlanFechaDB.fecha.in_(fechas)).all()
        cambios = {c.fecha: por_id[c.plan_id] for c in filas if c.plan_id in por_id}
    return {f: cambios.get(f) or semana[date.fromisoformat(f).weekday()] for f in fechas}


def plan_de_fecha(db, usuario_id: int, fecha: str, crear: bool = False) -> PlanNutricionDB:
    return planes_por_fecha(db, usuario_id, [fecha], crear)[fecha]


def sincronizar_principal(db, perfil: PerfilDB, comidas: Optional[List[str]] = None) -> None:
    """Las metas del perfil son las del plan principal: al cambiar unas se cambian las otras.
    Las comidas del día solo se guardan en el plan (el perfil las lee de ahí)."""
    principal = _planes(db, perfil.usuario_id, crear=True)[0]
    _copiar_metas(perfil, principal)
    _poner_comidas(principal, comidas)


def comidas_principal(db, usuario_id: int) -> List[str]:
    return comidas_de(_planes(db, usuario_id, crear=False)[0])


# --- Operaciones de la API ---

def _a_modelo(plan: PlanNutricionDB) -> Plan:
    return Plan(id=plan.id, nombre=plan.nombre, es_principal=bool(plan.es_principal), dias_semana=_dias(plan),
                comidas=comidas_de(plan), **{c: round(getattr(plan, c) or 0.0, 1) for c in CAMPOS_METAS})


def _resumen(planes: List[PlanNutricionDB]) -> PlanesUsuario:
    semana = _plan_semanal(planes)
    return PlanesUsuario(planes=[_a_modelo(p) for p in planes], semana=[semana[d].id for d in range(7)])


def _plan_del_usuario(db, usuario_id: int, plan_id: int) -> Optional[PlanNutricionDB]:
    return db.query(PlanNutricionDB).filter(
        PlanNutricionDB.id == plan_id, PlanNutricionDB.usuario_id == usuario_id).first()


def listar_planes(usuario_id: int) -> PlanesUsuario:
    db = SessionLocal()
    try:
        return _resumen(_planes(db, usuario_id, crear=True))
    finally:
        db.close()


def crear_plan(datos: PlanEntrada, usuario_id: int) -> Plan:
    db = SessionLocal()
    try:
        _planes(db, usuario_id, crear=True)  # el principal siempre existe antes que los demás
        plan = PlanNutricionDB(usuario_id=usuario_id, nombre=datos.nombre.strip(), es_principal=0, dias_semana="")
        _copiar_metas(datos, plan)
        _poner_comidas(plan, datos.comidas)
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return _a_modelo(plan)
    finally:
        db.close()


def actualizar_plan(plan_id: int, datos: PlanEntrada, usuario_id: int) -> Optional[Plan]:
    db = SessionLocal()
    try:
        plan = _plan_del_usuario(db, usuario_id, plan_id)
        if not plan:
            return None
        plan.nombre = datos.nombre.strip()
        _copiar_metas(datos, plan)
        _poner_comidas(plan, datos.comidas)
        if plan.es_principal:
            perfil = db.query(PerfilDB).filter(PerfilDB.usuario_id == usuario_id).first()
            if perfil:
                _copiar_metas(datos, perfil)
        db.commit()
        db.refresh(plan)
        return _a_modelo(plan)
    finally:
        db.close()


def eliminar_plan(plan_id: int, usuario_id: int) -> bool:
    """Borra un plan; sus días de la semana y sus cambios puntuales vuelven al plan principal."""
    db = SessionLocal()
    try:
        plan = _plan_del_usuario(db, usuario_id, plan_id)
        if not plan:
            return False
        if plan.es_principal:
            raise PlanNoValido("El plan principal no se puede borrar: son las metas de tu perfil.")
        db.query(PlanFechaDB).filter(PlanFechaDB.usuario_id == usuario_id, PlanFechaDB.plan_id == plan_id).delete()
        db.delete(plan)
        db.commit()
        return True
    finally:
        db.close()


def asignar_semana(datos: AsignacionSemana, usuario_id: int) -> PlanesUsuario:
    db = SessionLocal()
    try:
        planes = _planes(db, usuario_id, crear=True)
        por_id = {p.id: p for p in planes}
        if any(pid not in por_id for pid in datos.semana):
            raise PlanNoValido("Plan no encontrado")
        for plan in planes:
            plan.dias_semana = ",".join(str(d) for d, pid in enumerate(datos.semana) if pid == plan.id)
        db.commit()
        return _resumen(planes)
    finally:
        db.close()


def _dia(fecha: str, plan: PlanNutricionDB, semanal: PlanNutricionDB) -> PlanDelDia:
    return PlanDelDia(fecha=fecha, plan_id=plan.id, nombre=plan.nombre, calorias_objetivo=round(plan.calorias_objetivo, 1),
                      plan_semanal_id=semanal.id, cambiado=plan.id != semanal.id)


def obtener_semana(usuario_id: int, dia: Optional[str] = None) -> List[PlanDelDia]:
    """Plan de cada día de la semana (lunes a domingo) que contiene `dia` (por defecto, hoy)."""
    base = date.fromisoformat(dia) if dia else date.today()
    lunes = base - timedelta(days=base.weekday())
    fechas = [(lunes + timedelta(days=i)).isoformat() for i in range(7)]
    db = SessionLocal()
    try:
        aplicados = planes_por_fecha(db, usuario_id, fechas, crear=True)
        semana = _plan_semanal(_planes(db, usuario_id, crear=False))
        return [_dia(f, aplicados[f], semana[i]) for i, f in enumerate(fechas)]
    finally:
        db.close()


def cambiar_plan_fecha(usuario_id: int, fecha: str, plan_id: Optional[int]) -> PlanDelDia:
    """Usa otro plan solo en esa fecha. Elegir el plan que ya toca por semana (o null) quita el cambio."""
    dia_semana = date.fromisoformat(fecha).weekday()
    db = SessionLocal()
    try:
        planes = _planes(db, usuario_id, crear=True)
        semanal = _plan_semanal(planes)[dia_semana]
        if plan_id is not None and plan_id not in {p.id for p in planes}:
            raise PlanNoValido("Plan no encontrado")

        cambio = db.query(PlanFechaDB).filter(PlanFechaDB.usuario_id == usuario_id, PlanFechaDB.fecha == fecha).first()
        if plan_id is None or plan_id == semanal.id:
            if cambio:
                db.delete(cambio)
        elif cambio:
            cambio.plan_id = plan_id
        else:
            db.add(PlanFechaDB(usuario_id=usuario_id, fecha=fecha, plan_id=plan_id))
        db.commit()
        return _dia(fecha, plan_de_fecha(db, usuario_id, fecha), semanal)
    finally:
        db.close()
