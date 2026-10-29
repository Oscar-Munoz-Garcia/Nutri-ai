"""Buscador de alimentos para añadirlos al diario por gramos: primero los de la despensa del usuario
y después una base de alimentos comunes con valores medios por 100 g (tablas BEDCA / USDA)."""
import unicodedata
from typing import List

from app.db.models import PantryDB
from app.db.session import SessionLocal
from app.models.food import AlimentoPor100g

# nombre, nombre en inglés, kcal, proteínas, carbohidratos, grasas (por 100 g)
BASE_ALIMENTOS = [
    ("Arroz blanco cocido", "White rice, cooked", 130, 2.7, 28.2, 0.3),
    ("Arroz blanco crudo", "White rice, raw", 358, 6.7, 79.0, 0.6),
    ("Arroz integral cocido", "Brown rice, cooked", 123, 2.7, 25.6, 1.0),
    ("Pasta cocida", "Pasta, cooked", 158, 5.8, 30.9, 0.9),
    ("Pasta cruda", "Pasta, raw", 359, 12.5, 72.0, 1.5),
    ("Pan blanco", "White bread", 265, 8.9, 49.0, 3.2),
    ("Pan integral", "Wholemeal bread", 247, 13.0, 41.0, 3.4),
    ("Copos de avena", "Rolled oats", 379, 13.2, 67.7, 6.5),
    ("Patata cocida", "Potato, boiled", 87, 1.9, 20.1, 0.1),
    ("Boniato asado", "Sweet potato, baked", 90, 2.0, 20.7, 0.2),
    ("Quinoa cocida", "Quinoa, cooked", 120, 4.4, 21.3, 1.9),
    ("Pechuga de pollo cruda", "Chicken breast, raw", 110, 23.1, 0.0, 1.6),
    ("Pechuga de pollo a la plancha", "Chicken breast, grilled", 165, 31.0, 0.0, 3.6),
    ("Muslo de pollo", "Chicken thigh", 177, 24.0, 0.0, 8.9),
    ("Pechuga de pavo", "Turkey breast", 104, 24.0, 0.0, 0.7),
    ("Ternera magra", "Lean beef", 131, 21.5, 0.0, 5.0),
    ("Carne picada de ternera", "Ground beef", 254, 17.2, 0.0, 20.0),
    ("Lomo de cerdo", "Pork loin", 143, 21.0, 0.0, 6.5),
    ("Jamón serrano", "Serrano ham", 241, 30.5, 0.0, 13.0),
    ("Jamón cocido", "Cooked ham", 113, 18.0, 1.5, 3.7),
    ("Salmón", "Salmon", 208, 20.4, 0.0, 13.4),
    ("Merluza", "Hake", 86, 17.8, 0.0, 1.3),
    ("Atún al natural (lata)", "Tuna in water (canned)", 116, 25.5, 0.0, 0.8),
    ("Atún en aceite (lata)", "Tuna in oil (canned)", 198, 29.1, 0.0, 8.2),
    ("Gambas", "Prawns", 85, 18.0, 0.9, 0.9),
    ("Huevo", "Egg", 143, 12.6, 0.7, 9.5),
    ("Clara de huevo", "Egg white", 52, 10.9, 0.7, 0.2),
    ("Tofu", "Tofu", 144, 15.8, 2.8, 8.7),
    ("Lentejas cocidas", "Lentils, cooked", 116, 9.0, 20.1, 0.4),
    ("Garbanzos cocidos", "Chickpeas, cooked", 164, 8.9, 27.4, 2.6),
    ("Alubias cocidas", "Beans, cooked", 127, 8.7, 22.8, 0.5),
    ("Leche entera", "Whole milk", 63, 3.2, 4.7, 3.6),
    ("Leche semidesnatada", "Semi-skimmed milk", 46, 3.3, 4.8, 1.6),
    ("Leche desnatada", "Skimmed milk", 34, 3.4, 4.9, 0.1),
    ("Bebida de avena", "Oat drink", 45, 0.5, 6.6, 1.5),
    ("Yogur natural", "Plain yogurt", 61, 3.5, 4.7, 3.3),
    ("Yogur griego", "Greek yogurt", 115, 6.4, 4.0, 8.4),
    ("Yogur proteico / skyr", "Skyr / protein yogurt", 63, 11.0, 4.0, 0.2),
    ("Queso fresco batido 0%", "Quark 0% fat", 50, 8.0, 3.8, 0.2),
    ("Queso fresco", "Fresh cheese", 174, 12.4, 2.5, 12.8),
    ("Queso curado", "Cured cheese", 402, 25.0, 1.3, 33.0),
    ("Mozzarella", "Mozzarella", 280, 22.2, 2.2, 20.3),
    ("Proteína whey (polvo)", "Whey protein (powder)", 380, 78.0, 6.0, 5.5),
    ("Tomate", "Tomato", 18, 0.9, 3.9, 0.2),
    ("Tomate triturado", "Crushed tomato", 32, 1.6, 5.4, 0.3),
    ("Tomate frito", "Tomato sauce", 74, 1.5, 9.4, 3.4),
    ("Lechuga", "Lettuce", 15, 1.4, 2.9, 0.2),
    ("Espinacas", "Spinach", 23, 2.9, 3.6, 0.4),
    ("Brócoli", "Broccoli", 34, 2.8, 6.6, 0.4),
    ("Calabacín", "Courgette", 17, 1.2, 3.1, 0.3),
    ("Pimiento", "Pepper", 26, 1.0, 6.0, 0.3),
    ("Cebolla", "Onion", 40, 1.1, 9.3, 0.1),
    ("Zanahoria", "Carrot", 41, 0.9, 9.6, 0.2),
    ("Champiñones", "Mushrooms", 22, 3.1, 3.3, 0.3),
    ("Plátano", "Banana", 89, 1.1, 22.8, 0.3),
    ("Manzana", "Apple", 52, 0.3, 13.8, 0.2),
    ("Naranja", "Orange", 47, 0.9, 11.8, 0.1),
    ("Fresas", "Strawberries", 32, 0.7, 7.7, 0.3),
    ("Arándanos", "Blueberries", 57, 0.7, 14.5, 0.3),
    ("Kiwi", "Kiwi", 61, 1.1, 14.7, 0.5),
    ("Aguacate", "Avocado", 160, 2.0, 8.5, 14.7),
    ("Aceite de oliva", "Olive oil", 884, 0.0, 0.0, 100.0),
    ("Mantequilla", "Butter", 717, 0.9, 0.1, 81.1),
    ("Crema de cacahuete", "Peanut butter", 588, 25.1, 20.0, 50.4),
    ("Almendras", "Almonds", 579, 21.2, 21.6, 49.9),
    ("Nueces", "Walnuts", 654, 15.2, 13.7, 65.2),
    ("Chocolate negro 85%", "Dark chocolate 85%", 600, 11.0, 19.0, 50.0),
    ("Miel", "Honey", 304, 0.3, 82.4, 0.0),
    ("Azúcar", "Sugar", 387, 0.0, 100.0, 0.0),
]


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").strip()


def _coincide(consulta: str, *nombres: str) -> bool:
    """Todas las palabras de la búsqueda aparecen en alguno de los nombres ('pollo plancha', 'arroz coc')."""
    palabras = _normalizar(consulta).split()
    return any(all(p in _normalizar(n) for p in palabras) for n in nombres if n)


def buscar_alimentos(consulta: str, usuario_id: int, limite: int = 12) -> List[AlimentoPor100g]:
    consulta = (consulta or "").strip()
    if not consulta:
        return []
    db = SessionLocal()
    try:
        despensa = db.query(PantryDB).filter(PantryDB.usuario_id == usuario_id).all()
    finally:
        db.close()

    resultados = [
        AlimentoPor100g(nombre=p.nombre, origen="despensa", calorias_100g=p.calorias_100g or 0.0,
                        proteinas_100g=p.proteinas_100g or 0.0, carbohidratos_100g=p.carbohidratos_100g or 0.0,
                        grasas_100g=p.grasas_100g or 0.0)
        for p in despensa if _coincide(consulta, p.nombre)
    ]
    resultados += [
        AlimentoPor100g(nombre=es, nombre_en=en, origen="base", calorias_100g=kcal, proteinas_100g=prot,
                        carbohidratos_100g=carb, grasas_100g=gras)
        for es, en, kcal, prot, carb, gras in BASE_ALIMENTOS if _coincide(consulta, es, en)
    ]
    return resultados[:limite]
