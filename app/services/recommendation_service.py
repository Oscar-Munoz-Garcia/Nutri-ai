from typing import List
from app.models.recommendation import SolicitudRecomendacion, RecomendacionResultado
from app.services import recipe_service, pantry_service, daily_service


def obtener_sugerencias_recetas(solicitud: SolicitudRecomendacion, usuario_id: int) -> List[RecomendacionResultado]:
    # 1. Obtener ingesta del día actual para calcular macros restantes
    resumen_diario = daily_service.obtener_resumen_diario(usuario_id)
    
    cal_restantes = max(0.0, solicitud.calorias_objetivo - resumen_diario.calorias_totales)
    prot_restantes = max(0.0, solicitud.proteinas_objetivo - resumen_diario.proteinas_totales)
    
    # 2. Obtener recetas filtradas por utensilios
    recetas = recipe_service.listar_recetas(usuario_id, utensilios_disponibles=solicitud.utensilios_disponibles)
    
    # 3. Obtener despensa actual
    despensa = pantry_service.obtener_despensa(usuario_id)
    nombres_despensa = [item.nombre.strip().lower() for item in despensa if item.cantidad_gramos > 0]
    
    resultados: List[RecomendacionResultado] = []
    
    for receta in recetas:
        # Evaluar ingredientes faltantes en despensa
        faltantes = []
        for ing in receta.ingredientes:
            if ing.nombre.strip().lower() not in nombres_despensa:
                faltantes.append(ing.nombre)
                
        # Puntuación de coincidencia calórica (100% = encaja perfecto con las calorías restantes)
        if cal_restantes > 0:
            diferencia_cal = abs(cal_restantes - receta.calorias_totales)
            coincidencia = max(0.0, 100.0 - (diferencia_cal / cal_restantes * 100.0))
        else:
            coincidencia = 50.0

        # Penalización ligera si faltan ingredientes de la despensa
        if faltantes:
            coincidencia = max(0.0, coincidencia - (len(faltantes) * 15.0))

        explicacion = (
            f"Aporta {receta.calorias_totales} kcal y {receta.proteinas_totales}g de proteína. "
            f"Ajuste al hueco calórico restante de {round(cal_restantes, 1)} kcal."
        )

        resultados.append(
            RecomendacionResultado(
                receta=receta,
                coincidencia_porcentaje=round(coincidencia, 1),
                ingredientes_faltantes=faltantes,
                puntuacion_explicacion=explicacion
            )
        )

    # Ordenar sugerencias por mayor porcentaje de coincidencia
    resultados.sort(key=lambda x: x.coincidencia_porcentaje, reverse=True)
    return resultados