from typing import List
from app.models.daily import ObjetivosMacros, RegistroConsumo, ResumenDiario

# Estado en memoria del diario nutricional
_objetivos_actuales = ObjetivosMacros(
    calorias_objetivo=2200.0,
    proteinas_objetivo=160.0,
    carbohidratos_objetivo=210.0,
    grasas_objetivo=70.0
)

_registros_dia: List[RegistroConsumo] = []


def establecer_objetivos(objetivos: ObjetivosMacros) -> ObjetivosMacros:
    global _objetivos_actuales
    _objetivos_actuales = objetivos
    return _objetivos_actuales


def registrar_consumo(registro: RegistroConsumo) -> RegistroConsumo:
    _registros_dia.append(registro)
    return registro


def obtener_resumen_diario() -> ResumenDiario:
    cal_tot = sum(r.calorias for r in _registros_dia)
    prot_tot = sum(r.proteinas for r in _registros_dia)
    carb_tot = sum(r.carbohidratos for r in _registros_dia)
    gras_tot = sum(r.grasas for r in _registros_dia)

    return ResumenDiario(
        calorias_totales=round(cal_tot, 1),
        proteinas_totales=round(prot_tot, 1),
        carbohidratos_totales=round(carb_tot, 1),
        grasas_totales=round(gras_tot, 1),
        objetivos=_objetivos_actuales,
        calorias_restantes=round(max(0.0, _objetivos_actuales.calorias_objetivo - cal_tot), 1),
        proteinas_restantes=round(max(0.0, _objetivos_actuales.proteinas_objetivo - prot_tot), 1),
        carbohidratos_restantes=round(max(0.0, _objetivos_actuales.carbohidratos_objetivo - carb_tot), 1),
        grasas_restantes=round(max(0.0, _objetivos_actuales.grasas_objetivo - gras_tot), 1),
        registros=_registros_dia
    )