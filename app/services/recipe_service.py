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
    """Crea un catálogo inicial con recetas de muestra si no existe el archivo."""
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
        },
        {
            "id": "rec_002",
            "nombre": "Batido Proteico de Avena y Plátano",
            "descripcion": "Ideal para desayuno o post-entreno rápido.",
            "tiempo_preparacion_min": 5,
            "utensilios_necesarios": ["batidora"],
            "ingredientes": [
                {
                    "nombre": "Harina de avena",
                    "cantidad_gramos": 60,
                    "calorias_100g": 380,
                    "proteinas_100g": 12,
                    "carbohidratos_100g": 66,
                    "grasas_100g": 7
                },
                {
                    "nombre": "Proteína en polvo (Whey)",
                    "cantidad_gramos": 30,
                    "calorias_100g": 370,
                    "proteinas_100g": 80,
                    "carbohidratos_100g": 5,
                    "grasas_100g": 3
                },
                {
                    "nombre": "Plátano",
                    "cantidad_gramos": 100,
                    "calorias_100g": 89,
                    "proteinas_100g": 1.1,
                    "carbohidratos_100g": 23,
                    "grasas_100g": 0.3
                }
            ],
            "pasos": [
                "Añadir 300ml de agua o leche en el vaso de la batidora.",
                "Agregar la avena, proteína y plátano y batir 45 segundos."
            ],
            "calorias_totales": 428.0,
            "proteinas_totales": 32.3,
            "carbohidratos_totales": 64.1,
            "grasas_totales": 5.4
        }
    ]
    _guardar_recetas(recetas_base)


def calcular_macros_receta(ingredientes: List[IngredienteReceta]) -> dict:
    """Calcula de forma determinista el total de calorías y macros sumando los ingredientes."""
    cal_tot = 0.0
    prot_tot = 0.0
    carb_tot = 0.0
    gras_tot = 0.0

    for ing in ingredientes:
        factor = ing.cantidad_gramos / 100.0
        cal_tot += ing.calorias_100g * factor
        prot_tot += ing.proteinas_100g * factor
        carb_tot += ing.carbohidratos_100g * factor
        gras_tot += ing.grasas_100g * factor

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

    # Convertir lista de utensilios a minúsculas
    utensilios_usuario = set([u.strip().lower() for u in utensilios_disponibles])

    # Filtrar solo recetas cuyos utensilios requeridos estén todos disponibles
    recetas_filtradas = []
    for r in recetas_raw:
        requeridos = set([u.strip().lower() for u in r.get("utensilios_necesarios", [])])
        if requeridos.issubset(utensilios_usuario):
            recetas_filtradas.append(RecetaSalida(**r))

    return recetas_filtradas

from typing import List
from app.models.recipe import Receta, RecetaCrear

# Base de datos local en memoria
RECETAS_DB: List[Receta] = [
    Receta(
        id=1,
        nombre="Tortilla Proteica de Claras y Pavo",
        descripcion="Tortilla rápida alta en proteína para desayuno o cena.",
        calorias_totales=280.0,
        proteinas_totales=35.0,
        carbohidratos_totales=4.0,
        grasas_totales=12.0,
        tiempo_preparacion_min=10,
        utensilios_necesarios=["Sartén", "Batidor"]
    ),
    Receta(
        id=2,
        nombre="Pollo al Air Fryer con Arroz Integrada",
        descripcion="Pechuga sazonada en freidora de aire acompañada de arroz.",
        calorias_totales=450.0,
        proteinas_totales=42.0,
        carbohidratos_totales=48.0,
        grasas_totales=8.0,
        tiempo_preparacion_min=20,
        utensilios_necesarios=["Air Fryer"]
    )
]


def obtener_todas_las_recetas() -> List[Receta]:
    return RECETAS_DB


def crear_nueva_receta(datos: RecetaCrear) -> Receta:
    nuevo_id = max([r.id for r in RECETAS_DB], default=0) + 1
    nueva_receta = Receta(id=nuevo_id, **datos.model_dump())
    RECETAS_DB.append(nueva_receta)
    return nueva_receta