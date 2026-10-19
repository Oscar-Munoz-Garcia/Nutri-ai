import json
import os
import uuid
from typing import List, Optional
from app.models.recipe import RecetaEntrada, RecetaSalida, IngredienteReceta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
RECIPES_FILE = os.path.join(DATA_DIR, "recipes.json")

os.makedirs(DATA_DIR, exist_ok=True)


def _leer_recetas() -> list:
    if not os.path.exists(RECIPES_FILE):
        _inicializar_recetas_demo()
    try:
        with open(RECIPES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _guardar_recetas(data: list) -> None:
    with open(RECIPES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _inicializar_recetas_demo():
    recetas_base = [
        {
            "id": "rec_001",
            "nombre": "Pechuga de Pollo Crujiente en Airfryer",
            "descripcion": "Pollo sazonado super jugoso preparado sin aceite.",
            "tiempo_preparacion_min": 15,
            "utensilios_necesarios": ["airfryer"],
            "ingredientes": [
                {
                    "nombre": "Pechuga de pollo",
                    "cantidad_gramos": 200,
                    "calorias_100g": 165,
                    "proteinas_100g": 31,
                    "carbohidratos_100g": 0,
                    "grasas_100g": 3.6
                },
                {
                    "nombre": "Aceite de oliva (spray)",
                    "cantidad_gramos": 5,
                    "calorias_100g": 884,
                    "proteinas_100g": 0,
                    "carbohidratos_100g": 0,
                    "grasas_100g": 100
                }
            ],
            "pasos": [
                "Sazonar la pechuga con sal, pimienta y ajo en polvo.",
                "Pulverizar el aceite y colocar en la Airfryer a 190°C durante 12 minutos."
            ],
            "calorias_totales": 374.2,
            "proteinas_totales": 62.0,
            "carbohidratos_totales": 0.0,
            "grasas_totales": 12.2
        }
    ]
    _guardar_recetas(recetas_base)


def calcular_macros_receta(ingredientes: List[IngredienteReceta]) -> dict:
    cal_tot = sum((ing.calorias_100g * ing.cantidad_gramos / 100.0) for ing in ingredientes)
    prot_tot = sum((ing.proteinas_100g * ing.cantidad_gramos / 100.0) for ing in ingredientes)
    carb_tot = sum((ing.carbohidratos_100g * ing.cantidad_gramos / 100.0) for ing in ingredientes)
    gras_tot = sum((ing.grasas_100g * ing.cantidad_gramos / 100.0) for ing in ingredientes)

    return {
        "calorias_totales": round(cal_tot, 1),
        "proteinas_totales": round(prot_tot, 1),
        "carbohidratos_totales": round(carb_tot, 1),
        "grasas_totales": round(gras_tot, 1)
    }


def crear_receta(entrada: RecetaEntrada) -> RecetaSalida:
    recetas = _leer_recetas()
    macros = calcular_macros_receta(entrada.ingredientes)
    
    receta_dict = entrada.model_dump()
    receta_dict["id"] = "rec_" + str(uuid.uuid4())[:8]
    receta_dict["utensilios_necesarios"] = [u.strip().lower() for u in entrada.utensilios_necesarios]
    receta_dict.update(macros)

    recetas.append(receta_dict)
    _guardar_recetas(recetas)
    return RecetaSalida(**receta_dict)


def listar_recetas(utensilios_disponibles: Optional[List[str]] = None) -> List[RecetaSalida]:
    recetas_raw = _leer_recetas()
    
    if not utensilios_disponibles:
        return [RecetaSalida(**r) for r in recetas_raw]

    utensilios_usuario = set([u.strip().lower() for u in utensilios_disponibles])
    recetas_filtradas = []
    for r in recetas_raw:
        requeridos = set([u.strip().lower() for u in r.get("utensilios_necesarios", [])])
        if requeridos.issubset(utensilios_usuario):
            recetas_filtradas.append(RecetaSalida(**r))

    return recetas_filtradas