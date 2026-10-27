from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from app.db.session import SessionLocal
from app.db.models import UsuarioDB, PerfilDB, PesoHistorialDB, RegistroConsumoDB
from app.models.metabolic import (
    PesoEntrada, PesoRegistro, TDEEDinamico, DiaCumplimiento, CumplimientoUsuario, Versus
)
from app.models.profile import PerfilUsuario
from app.services.profile_service import calcular_mifflin_st_jeor

# Energía aproximada de 1 kg de tejido corporal (mezcla grasa/magro)
KCAL_POR_KG = 7700.0

# Requisitos mínimos para que la regresión sea fiable
MIN_PESAJES = 3
MIN_DIAS_ENTRE_PESAJES = 7
MIN_DIAS_CON_REGISTRO = 7

# Tolerancia calórica: 100% dentro de ±10% de la meta, 0% a partir de ±30%
TOLERANCIA_CAL_OK = 0.10
TOLERANCIA_CAL_MAX = 0.30


# --- UTILIDADES PURAS (sin BD, testeables) ---

def regresion_lineal(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """Mínimos cuadrados simples. Devuelve (pendiente, intercepto, r2)."""
    n = len(xs)
    media_x = sum(xs) / n
    media_y = sum(ys) / n
    sxx = sum((x - media_x) ** 2 for x in xs)
    sxy = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys))
    if sxx == 0:
        return 0.0, media_y, 0.0
    pendiente = sxy / sxx
    intercepto = media_y - pendiente * media_x
    ss_tot = sum((y - media_y) ** 2 for y in ys)
    ss_res = sum((y - (pendiente * x + intercepto)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return pendiente, intercepto, r2


def calcular_tdee(ingestas: Dict[str, float], pesajes: List[Tuple[str, float]]) -> Optional[Dict[str, float]]:
    """
    Balance energético: TDEE = ingesta media - (variación de peso diaria * 7700 kcal/kg).
    La variación diaria es la pendiente de la regresión lineal peso~día, que suaviza
    el ruido de agua/glucógeno entre pesajes. Devuelve None si faltan datos.
    """
    dias_con_registro = [kcal for kcal in ingestas.values() if kcal > 0]
    if len(pesajes) < MIN_PESAJES or len(dias_con_registro) < MIN_DIAS_CON_REGISTRO:
        return None

    pesajes = sorted(pesajes)
    origen = date.fromisoformat(pesajes[0][0])
    xs = [(date.fromisoformat(f) - origen).days for f, _ in pesajes]
    ys = [p for _, p in pesajes]
    if xs[-1] - xs[0] < MIN_DIAS_ENTRE_PESAJES:
        return None

    pendiente, intercepto, r2 = regresion_lineal(xs, ys)
    ingesta_media = sum(dias_con_registro) / len(dias_con_registro)
    return {
        "tdee": ingesta_media - pendiente * KCAL_POR_KG,
        "ingesta_media": ingesta_media,
        "pendiente_kg_dia": pendiente,
        "intercepto": intercepto,
        "r2": r2,
        "xs": xs,
    }


def puntuar_dia(calorias: float, proteinas: float, meta_cal: float, meta_prot: float) -> float:
    """Puntuación 0-1 de un día: media entre precisión calórica y proteína alcanzada."""
    if calorias <= 0:
        return 0.0
    desviacion = abs(calorias - meta_cal) / meta_cal if meta_cal > 0 else 0.0
    if desviacion <= TOLERANCIA_CAL_OK:
        score_cal = 1.0
    else:
        score_cal = max(0.0, 1.0 - (desviacion - TOLERANCIA_CAL_OK) / (TOLERANCIA_CAL_MAX - TOLERANCIA_CAL_OK))
    score_prot = min(1.0, proteinas / meta_prot) if meta_prot > 0 else 1.0
    return (score_cal + score_prot) / 2


# --- ACCESO A DATOS ---

def _perfil_de(db, usuario_id: int) -> Optional[PerfilDB]:
    return db.query(PerfilDB).filter(PerfilDB.usuario_id == usuario_id).first()


def _ingestas_por_dia(db, usuario_id: int, fechas: List[str]) -> Dict[str, Tuple[float, float]]:
    totales = {f: [0.0, 0.0] for f in fechas}
    registros = db.query(RegistroConsumoDB).filter(
        RegistroConsumoDB.fecha.in_(fechas),
        RegistroConsumoDB.usuario_id == usuario_id
    ).all()
    for r in registros:
        totales[r.fecha][0] += r.calorias or 0.0
        totales[r.fecha][1] += r.proteinas or 0.0
    return {f: (c, p) for f, (c, p) in totales.items()}


# --- REGISTRO DE PESO ---

def registrar_peso(entrada: PesoEntrada, usuario_id: int) -> PesoRegistro:
    fecha = entrada.fecha or date.today().isoformat()
    date.fromisoformat(fecha)  # valida formato
    db = SessionLocal()
    try:
        # Un pesaje por día: si ya existe, se sobrescribe
        registro = db.query(PesoHistorialDB).filter(
            PesoHistorialDB.usuario_id == usuario_id, PesoHistorialDB.fecha == fecha
        ).first()
        if registro:
            registro.peso_kg = entrada.peso_kg
        else:
            registro = PesoHistorialDB(usuario_id=usuario_id, fecha=fecha, peso_kg=entrada.peso_kg)
            db.add(registro)

        # Mantener el peso del perfil sincronizado con el pesaje más reciente
        ultimo = db.query(PesoHistorialDB).filter(PesoHistorialDB.usuario_id == usuario_id) \
            .order_by(PesoHistorialDB.fecha.desc()).first()
        if not ultimo or fecha >= ultimo.fecha:
            perfil = _perfil_de(db, usuario_id)
            if perfil:
                perfil.peso_kg = entrada.peso_kg

        db.commit()
        db.refresh(registro)
        return PesoRegistro(id=registro.id, fecha=registro.fecha, peso_kg=registro.peso_kg)
    finally:
        db.close()


def listar_pesos(usuario_id: int, dias: int = 90) -> List[PesoRegistro]:
    desde = (date.today() - timedelta(days=dias - 1)).isoformat()
    db = SessionLocal()
    try:
        filas = db.query(PesoHistorialDB).filter(
            PesoHistorialDB.usuario_id == usuario_id, PesoHistorialDB.fecha >= desde
        ).order_by(PesoHistorialDB.fecha).all()
        return [PesoRegistro(id=p.id, fecha=p.fecha, peso_kg=p.peso_kg) for p in filas]
    finally:
        db.close()


def eliminar_peso(peso_id: int, usuario_id: int) -> bool:
    db = SessionLocal()
    try:
        fila = db.query(PesoHistorialDB).filter(
            PesoHistorialDB.id == peso_id, PesoHistorialDB.usuario_id == usuario_id
        ).first()
        if not fila:
            return False
        db.delete(fila)
        db.commit()
        return True
    finally:
        db.close()


# --- TDEE DINÁMICO ---

def obtener_tdee_dinamico(usuario_id: int, dias: int = 28) -> TDEEDinamico:
    hoy = date.today()
    fechas = [(hoy - timedelta(days=i)).isoformat() for i in range(dias - 1, -1, -1)]
    db = SessionLocal()
    try:
        perfil = _perfil_de(db, usuario_id)
        perfil_modelo = PerfilUsuario(
            nombre=perfil.nombre, edad=perfil.edad, peso_kg=perfil.peso_kg, altura_cm=perfil.altura_cm,
            genero=perfil.genero, nivel_actividad=perfil.nivel_actividad
        ) if perfil else PerfilUsuario()
        tdee_teorico = calcular_mifflin_st_jeor(perfil_modelo).calorias_objetivo

        ingestas = {f: c for f, (c, _) in _ingestas_por_dia(db, usuario_id, fechas).items()}
        filas = db.query(PesoHistorialDB).filter(
            PesoHistorialDB.usuario_id == usuario_id, PesoHistorialDB.fecha >= fechas[0]
        ).order_by(PesoHistorialDB.fecha).all()
    finally:
        db.close()

    pesajes = [PesoRegistro(id=p.id, fecha=p.fecha, peso_kg=p.peso_kg) for p in filas]
    dias_con_registro = sum(1 for c in ingestas.values() if c > 0)
    base = dict(
        tdee_teorico=round(tdee_teorico),
        dias_ventana=dias,
        dias_con_registro=dias_con_registro,
        num_pesajes=len(pesajes),
        pesajes=pesajes,
    )

    resultado = calcular_tdee(ingestas, [(p.fecha, p.peso_kg) for p in pesajes])
    if not resultado:
        faltan = []
        if len(pesajes) < MIN_PESAJES:
            faltan.append(f"{MIN_PESAJES - len(pesajes)} pesaje(s) más")
        elif (date.fromisoformat(pesajes[-1].fecha) - date.fromisoformat(pesajes[0].fecha)).days < MIN_DIAS_ENTRE_PESAJES:
            faltan.append(f"pesajes separados al menos {MIN_DIAS_ENTRE_PESAJES} días")
        if dias_con_registro < MIN_DIAS_CON_REGISTRO:
            faltan.append(f"{MIN_DIAS_CON_REGISTRO - dias_con_registro} día(s) más con comidas registradas")
        return TDEEDinamico(
            estado="insuficiente",
            mensaje="Faltan datos para calcular tu TDEE real: " + ", ".join(faltan) + ". Mientras tanto se muestra el estimado por fórmula.",
            **base
        )

    tdee = round(resultado["tdee"])
    kg_semana = round(resultado["pendiente_kg_dia"] * 7, 2)
    recta = [round(resultado["pendiente_kg_dia"] * x + resultado["intercepto"], 2) for x in resultado["xs"]]
    return TDEEDinamico(
        estado="ok",
        mensaje=f"Con {round(resultado['ingesta_media'])} kcal/día de media tu peso varía {kg_semana:+.2f} kg/semana.",
        tdee_real=tdee,
        ingesta_media=round(resultado["ingesta_media"]),
        tendencia_kg_semana=kg_semana,
        r2=round(resultado["r2"], 2),
        recta=recta,
        **base
    )


# --- VERSUS / CUMPLIMIENTO SEMANAL ---

def _cumplimiento_semana(db, usuario_id: int, lunes: date, hasta: date,
                         meta_cal: float, meta_prot: float) -> List[DiaCumplimiento]:
    """Días de lunes a `hasta`. El día de hoy solo cuenta si ya tiene comidas registradas."""
    hoy = date.today()
    fechas = [(lunes + timedelta(days=i)).isoformat() for i in range((hasta - lunes).days + 1)]
    ingestas = _ingestas_por_dia(db, usuario_id, fechas)
    dias = []
    for f in fechas:
        cal, prot = ingestas[f]
        if f == hoy.isoformat() and cal <= 0:
            continue
        dias.append(DiaCumplimiento(
            fecha=f, calorias=round(cal), proteinas=round(prot, 1),
            puntuacion=round(puntuar_dia(cal, prot, meta_cal, meta_prot) * 100, 1)
        ))
    return dias


def _porcentaje(dias: List[DiaCumplimiento]) -> float:
    return round(sum(d.puntuacion for d in dias) / len(dias), 1) if dias else 0.0


def obtener_versus(usuario_actual_id: int) -> Versus:
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    lunes_anterior = lunes - timedelta(days=7)
    db = SessionLocal()
    try:
        participantes = []
        for usuario in db.query(UsuarioDB).order_by(UsuarioDB.id).all():
            perfil = _perfil_de(db, usuario.id)
            meta_cal = perfil.calorias_objetivo if perfil else 2200.0
            meta_prot = perfil.proteinas_objetivo if perfil else 160.0

            dias = _cumplimiento_semana(db, usuario.id, lunes, hoy, meta_cal, meta_prot)
            dias_ant = _cumplimiento_semana(db, usuario.id, lunes_anterior,
                                            lunes - timedelta(days=1), meta_cal, meta_prot)
            es_yo = usuario.id == usuario_actual_id
            if not es_yo:
                # Privacidad: del resto solo se comparte la puntuación, no lo que comen
                for d in dias:
                    d.calorias = d.proteinas = None
            participantes.append(CumplimientoUsuario(
                usuario_id=usuario.id,
                nombre=(perfil.nombre if perfil and perfil.nombre and perfil.nombre != "Usuario" else usuario.username),
                es_yo=es_yo,
                porcentaje_semana=_porcentaje(dias),
                porcentaje_semana_anterior=_porcentaje(dias_ant),
                dias_cumplidos=sum(1 for d in dias if d.puntuacion >= 90),
                dias_evaluados=len(dias),
                dias=dias,
            ))
    finally:
        db.close()

    participantes.sort(key=lambda p: p.porcentaje_semana, reverse=True)
    lider = participantes[0].usuario_id if participantes and participantes[0].porcentaje_semana > 0 else None
    return Versus(
        semana_inicio=lunes.isoformat(),
        semana_fin=(lunes + timedelta(days=6)).isoformat(),
        lider_id=lider,
        participantes=participantes,
    )
