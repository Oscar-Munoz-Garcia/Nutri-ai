from app.models.user import PerfilUsuario, ObjetivoMacros

# Multiplicadores de nivel de actividad
FACTOR_ACTIVIDAD = {
    "sedentario": 1.2,
    "ligero": 1.375,
    "moderado": 1.55,
    "alto": 1.725,
    "extremo": 1.9
}


def calcular_objetivo_macros(perfil: PerfilUsuario) -> ObjetivoMacros:
    """
    Calcula el BMR (Mifflin-St Jeor), TDEE y el reparto de macros según el objetivo.
    """
    # 1. Tasa Metabólica Basal (BMR)
    if perfil.genero == "hombre":
        bmr = (10 * perfil.peso_kg) + (6.25 * perfil.altura_cm) - (5 * perfil.edad) + 5
    else:
        bmr = (10 * perfil.peso_kg) + (6.25 * perfil.altura_cm) - (5 * perfil.edad) - 161

    # 2. Gasto Energético Total Diario (TDEE)
    tdee = bmr * FACTOR_ACTIVIDAD[perfil.nivel_actividad]

    # 3. Ajuste por objetivo
    if perfil.objetivo == "perder_grasa":
        calorias_target = tdee - 400  # Déficit calórico moderado
    elif perfil.objetivo == "ganar_masa":
        calorias_target = tdee + 300  # Superávit calórico moderado
    else:
        calorias_target = tdee

    # 4. Reparto de Macronutrientes
    # Proteína: 2.0g por kg para pérdida/ganancia o 1.8g para mantenimiento
    if perfil.objetivo in ["perder_grasa", "ganar_masa"]:
        proteinas_g = perfil.peso_kg * 2.0
    else:
        proteinas_g = perfil.peso_kg * 1.8

    # Grasas: 0.9g por kg de peso corporal
    grasas_g = perfil.peso_kg * 0.9

    # Carbohidratos: el resto de las calorías
    # (1g proteina = 4 kcal, 1g grasa = 9 kcal, 1g carbohidrato = 4 kcal)
    calorias_prot = proteinas_g * 4
    calorias_gras = grasas_g * 9
    calorias_restantes = calorias_target - (calorias_prot + calorias_gras)
    
    carbohidratos_g = max(calorias_restantes / 4, 50)  # Mínimo de seguridad de 50g

    return ObjetivoMacros(
        bmr_calorias=round(bmr),
        tdee_calorias=round(tdee),
        calorias_objetivo=round(calorias_target),
        proteinas_g=round(proteinas_g),
        carbohidratos_g=round(carbohidratos_g),
        grasas_g=round(grasas_g)
    )