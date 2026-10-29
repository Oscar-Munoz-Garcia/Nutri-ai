from app.models.profile import PerfilUsuario, PerfilActualizar, CuestionarioRegistro
from app.models.metabolic import PesoEntrada
from app.models.daily import ObjetivosMacros
from app.db.session import SessionLocal
from app.services import daily_service, plan_service

# Ajuste sobre el gasto calórico de mantenimiento según la meta del usuario
AJUSTE_OBJETIVO_KCAL = {"perder_grasa": -400, "mantenimiento": 0, "ganar_masa": 300}


def calcular_mifflin_st_jeor(perfil: PerfilUsuario) -> ObjetivosMacros:
    if perfil.genero == "hombre":
        tmb = (10 * perfil.peso_kg) + (6.25 * perfil.altura_cm) - (5 * perfil.edad) + 5
    else:
        tmb = (10 * perfil.peso_kg) + (6.25 * perfil.altura_cm) - (5 * perfil.edad) - 161

    factores = {"sedentario": 1.2, "ligero": 1.375, "moderado": 1.55, "intenso": 1.725}
    factor = factores.get(perfil.nivel_actividad, 1.55)
    calorias = round(tmb * factor + AJUSTE_OBJETIVO_KCAL.get(perfil.objetivo, 0), 1)

    prot_g = round(perfil.peso_kg * 2.0, 1)
    grasas_g = round((calorias * 0.25) / 9.0, 1)
    calorias_restantes = calorias - (prot_g * 4.0) - (grasas_g * 9.0)
    carbs_g = round(max(0.0, calorias_restantes / 4.0), 1)

    return ObjetivosMacros(
        calorias_objetivo=calorias,
        proteinas_objetivo=prot_g,
        carbohidratos_objetivo=carbs_g,
        grasas_objetivo=grasas_g
    )


def obtener_perfil(usuario_id: int) -> PerfilUsuario:
    db = SessionLocal()
    try:
        pdb = daily_service.obtener_o_crear_perfil_db(db, usuario_id)
        macros = ObjetivosMacros(
            calorias_objetivo=pdb.calorias_objetivo,
            proteinas_objetivo=pdb.proteinas_objetivo,
            carbohidratos_objetivo=pdb.carbohidratos_objetivo,
            grasas_objetivo=pdb.grasas_objetivo
        )
        return PerfilUsuario(
            nombre=pdb.nombre,
            apellidos=pdb.apellidos or "",
            objetivo=pdb.objetivo or "mantenimiento",
            edad=pdb.edad,
            peso_kg=pdb.peso_kg,
            altura_cm=pdb.altura_cm,
            genero=pdb.genero,
            nivel_actividad=pdb.nivel_actividad,
            modo_objetivo=pdb.modo_objetivo,
            objetivos_diarios=macros,
            dias_libres_semana=1 if pdb.dias_libres_semana is None else pdb.dias_libres_semana
        )
    finally:
        db.close()


def actualizar_perfil(datos: PerfilActualizar, usuario_id: int) -> PerfilUsuario:
    db = SessionLocal()
    try:
        pdb = daily_service.obtener_o_crear_perfil_db(db, usuario_id)

        if datos.nombre is not None: pdb.nombre = datos.nombre
        if datos.apellidos is not None: pdb.apellidos = datos.apellidos
        if datos.objetivo is not None: pdb.objetivo = datos.objetivo
        if datos.edad is not None: pdb.edad = datos.edad
        if datos.peso_kg is not None: pdb.peso_kg = datos.peso_kg
        if datos.altura_cm is not None: pdb.altura_cm = datos.altura_cm
        if datos.genero is not None: pdb.genero = datos.genero
        if datos.nivel_actividad is not None: pdb.nivel_actividad = datos.nivel_actividad
        if datos.dias_libres_semana is not None: pdb.dias_libres_semana = datos.dias_libres_semana
        pdb.modo_objetivo = datos.modo_objetivo

        perfil_temp = PerfilUsuario(
            nombre=pdb.nombre, edad=pdb.edad, peso_kg=pdb.peso_kg,
            altura_cm=pdb.altura_cm, genero=pdb.genero, nivel_actividad=pdb.nivel_actividad,
            objetivo=pdb.objetivo or "mantenimiento"
        )

        if datos.modo_objetivo == "manual_macros":
            prot = datos.proteinas_g if datos.proteinas_g is not None else pdb.proteinas_objetivo
            carb = datos.carbohidratos_g if datos.carbohidratos_g is not None else pdb.carbohidratos_objetivo
            gras = datos.grasas_g if datos.grasas_g is not None else pdb.grasas_objetivo
            cal = round((prot * 4.0) + (carb * 4.0) + (gras * 9.0), 1)
            nuevos_macros = ObjetivosMacros(calorias_objetivo=cal, proteinas_objetivo=prot, carbohidratos_objetivo=carb, grasas_objetivo=gras)

        elif datos.modo_objetivo == "manual_calorias":
            cal = datos.calorias_totales if datos.calorias_totales is not None else pdb.calorias_objetivo
            prot = round((cal * 0.30) / 4.0, 1)
            carb = round((cal * 0.40) / 4.0, 1)
            gras = round((cal * 0.30) / 9.0, 1)
            nuevos_macros = ObjetivosMacros(calorias_objetivo=cal, proteinas_objetivo=prot, carbohidratos_objetivo=carb, grasas_objetivo=gras)

        else:
            nuevos_macros = calcular_mifflin_st_jeor(perfil_temp)

        pdb.calorias_objetivo = nuevos_macros.calorias_objetivo
        pdb.proteinas_objetivo = nuevos_macros.proteinas_objetivo
        pdb.carbohidratos_objetivo = nuevos_macros.carbohidratos_objetivo
        pdb.grasas_objetivo = nuevos_macros.grasas_objetivo
        plan_service.sincronizar_principal(db, pdb)

        db.commit()
        db.refresh(pdb)

        return obtener_perfil(usuario_id)
    finally:
        db.close()


def completar_registro(datos: CuestionarioRegistro, usuario_id: int) -> PerfilUsuario:
    """Guarda el cuestionario de alta, calcula los objetivos diarios y marca el registro como completo."""
    actualizar_perfil(PerfilActualizar(
        nombre=datos.nombre.strip(), apellidos=datos.apellidos.strip(), edad=datos.edad,
        peso_kg=datos.peso_kg, altura_cm=datos.altura_cm, genero=datos.genero,
        nivel_actividad=datos.nivel_actividad, objetivo=datos.objetivo,
        modo_objetivo="mifflin_st_jeor"
    ), usuario_id)
    # Primer pesaje del historial, para que el TDEE dinámico tenga punto de partida
    from app.services import metabolic_service  # import local: metabolic_service importa este módulo
    metabolic_service.registrar_peso(PesoEntrada(peso_kg=datos.peso_kg), usuario_id)

    db = SessionLocal()
    try:
        pdb = daily_service.obtener_o_crear_perfil_db(db, usuario_id)
        pdb.registro_completo = 1
        db.commit()
    finally:
        db.close()
    return obtener_perfil(usuario_id)
