from app.models.profile import PerfilUsuario, PerfilActualizar
from app.models.daily import ObjetivosMacros
from app.services import daily_service

# Perfil por defecto en memoria
_perfil_actual = PerfilUsuario()


def calcular_mifflin_st_jeor(perfil: PerfilUsuario) -> ObjetivosMacros:
    """Calcula la Tasa Metabólica Basal (TMB) y el Gasto Calórico Total."""
    if perfil.genero == "hombre":
        tmb = (10 * perfil.peso_kg) + (6.25 * perfil.altura_cm) - (5 * perfil.edad) + 5
    else:
        tmb = (10 * perfil.peso_kg) + (6.25 * perfil.altura_cm) - (5 * perfil.edad) - 161

    factores = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "intenso": 1.725
    }
    factor = factores.get(perfil.nivel_actividad, 1.55)
    calorias = round(tmb * factor, 1)

    # Reparto estándar deportivo: 2g proteína/kg peso, 25% grasas, resto carbohidratos
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


def obtener_perfil() -> PerfilUsuario:
    return _perfil_actual


def actualizar_perfil(datos: PerfilActualizar) -> PerfilUsuario:
    global _perfil_actual

    # Actualizar datos personales si fueron enviados
    if datos.nombre is not None: _perfil_actual.nombre = datos.nombre
    if datos.edad is not None: _perfil_actual.edad = datos.edad
    if datos.peso_kg is not None: _perfil_actual.peso_kg = datos.peso_kg
    if datos.altura_cm is not None: _perfil_actual.altura_cm = datos.altura_cm
    if datos.genero is not None: _perfil_actual.genero = datos.genero
    if datos.nivel_actividad is not None: _perfil_actual.nivel_actividad = datos.nivel_actividad
    _perfil_actual.modo_objetivo = datos.modo_objetivo

    # Calcular u obtener los nuevos ObjetivosMacros
    if datos.modo_objetivo == "manual_macros":
        prot = datos.proteinas_g if datos.proteinas_g is not None else _perfil_actual.objetivos_diarios.proteinas_objetivo
        carb = datos.carbohidratos_g if datos.carbohidratos_g is not None else _perfil_actual.objetivos_diarios.carbohidratos_objetivo
        gras = datos.grasas_g if datos.grasas_g is not None else _perfil_actual.objetivos_diarios.grasas_objetivo
        cal = round((prot * 4.0) + (carb * 4.0) + (gras * 9.0), 1)

        nuevos_macros = ObjetivosMacros(
            calorias_objetivo=cal,
            proteinas_objetivo=prot,
            carbohidratos_objetivo=carb,
            grasas_objetivo=gras
        )

    elif datos.modo_objetivo == "manual_calorias":
        cal = datos.calorias_totales if datos.calorias_totales is not None else _perfil_actual.objetivos_diarios.calorias_objetivo
        # Reparto balanceado: 30% Proteína, 40% Carbohidratos, 30% Grasas
        prot = round((cal * 0.30) / 4.0, 1)
        carb = round((cal * 0.40) / 4.0, 1)
        gras = round((cal * 0.30) / 9.0, 1)

        nuevos_macros = ObjetivosMacros(
            calorias_objetivo=cal,
            proteinas_objetivo=prot,
            carbohidratos_objetivo=carb,
            grasas_objetivo=gras
        )

    else:  # mifflin_st_jeor
        nuevos_macros = calcular_mifflin_st_jeor(_perfil_actual)

    _perfil_actual.objetivos_diarios = nuevos_macros
    
    # Sincronizar automáticamente con el diario diario
    daily_service.establecer_objetivos(nuevos_macros)

    return _perfil_actual