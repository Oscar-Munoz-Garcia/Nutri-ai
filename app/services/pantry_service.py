import json
import os
import uuid
from datetime import datetime
from typing import List, Optional
from app.models.pantry import ItemDespensa, RegistroComidaEntrada, RegistroComidaSalida, ResumenDiarioMacros

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
PANTRY_FILE = os.path.join(DATA_DIR, "pantry.json")
LOGS_FILE = os.path.join(DATA_DIR, "food_logs.json")

os.makedirs(DATA_DIR, exist_ok=True)


def _leer_json(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _guardar_json(filepath: str, data: list) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- SERVICIOS DE DESPENSA ---

def listar_despensa() -> List[ItemDespensa]:
    raw_data = _leer_json(PANTRY_FILE)
    return [ItemDespensa(**item) for item in raw_data]


def agregar_o_actualizar_despensa(item: ItemDespensa) -> ItemDespensa:
    despensa = _leer_json(PANTRY_FILE)
    
    # Buscar si ya existe un item con el mismo nombre (case-insensitive)
    item_existente = next((i for i in despensa if i["nombre"].strip().lower() == item.nombre.strip().lower()), None)
    
    if item_existente:
        item_existente["cantidad_gramos"] += item.cantidad_gramos
        item_existente["calorias_100g"] = item.calorias_100g
        item_existente["proteinas_100g"] = item.proteinas_100g
        item_existente["carbohidratos_100g"] = item.carbohidratos_100g
        item_existente["grasas_100g"] = item.grasas_100g
        _guardar_json(PANTRY_FILE, despensa)
        return ItemDespensa(**item_existente)
    else:
        item_dict = item.model_dump()
        item_dict["id"] = str(uuid.uuid4())[:8]
        despensa.append(item_dict)
        _guardar_json(PANTRY_FILE, despensa)
        return ItemDespensa(**item_dict)


# --- SERVICIOS DE REGISTRO DIARIO ---

def registrar_comida(entrada: RegistroComidaEntrada) -> RegistroComidaSalida:
    logs = _leer_json(LOGS_FILE)
    
    factor = entrada.cantidad_gramos / 100.0
    cal_tot = round(entrada.calorias_100g * factor, 1)
    prot_tot = round(entrada.proteinas_100g * factor, 1)
    carb_tot = round(entrada.carbohidratos_100g * factor, 1)
    gras_tot = round(entrada.grasas_100g * factor, 1)
    
    registro_id = str(uuid.uuid4())[:8]
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    nuevo_registro = {
        "id": registro_id,
        "fecha": fecha_hoy,
        "nombre_alimento": entrada.nombre_alimento,
        "cantidad_gramos": entrada.cantidad_gramos,
        "momento_dia": entrada.momento_dia,
        "calorias_totales": cal_tot,
        "proteinas_totales": prot_tot,
        "carbohidratos_totales": carb_tot,
        "grasas_totales": gras_tot
    }
    
    logs.append(nuevo_registro)
    _guardar_json(LOGS_FILE, logs)
    
    # Descontar de despensa si aplica
    if entrada.descontar_de_despensa:
        despensa = _leer_json(PANTRY_FILE)
        for item in despensa:
            if item["nombre"].strip().lower() == entrada.nombre_alimento.strip().lower():
                item["cantidad_gramos"] = max(0.0, item["cantidad_gramos"] - entrada.cantidad_gramos)
                break
        _guardar_json(PANTRY_FILE, despensa)
        
    return RegistroComidaSalida(**nuevo_registro)


def obtener_resumen_diario(fecha_str: Optional[str] = None) -> ResumenDiarioMacros:
    if not fecha_str:
        fecha_str = datetime.now().strftime("%Y-%m-%d")
        
    logs = _leer_json(LOGS_FILE)
    comidas_del_dia = [c for c in logs if c["fecha"] == fecha_str]
    
    cal_tot = sum(c["calorias_totales"] for c in comidas_del_dia)
    prot_tot = sum(c["proteinas_totales"] for c in comidas_del_dia)
    carb_tot = sum(c["carbohidratos_totales"] for c in comidas_del_dia)
    gras_tot = sum(c["grasas_totales"] for c in comidas_del_dia)
    
    return ResumenDiarioMacros(
        fecha=fecha_str,
        calorias_totales=round(cal_tot, 1),
        proteinas_totales=round(prot_tot, 1),
        carbohidratos_totales=round(carb_tot, 1),
        grasas_totales=round(gras_tot, 1),
        comidas_registradas=[RegistroComidaSalida(**c) for c in comidas_del_dia]
    )